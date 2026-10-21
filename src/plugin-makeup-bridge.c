/* KattBeauty OBS Bridge 0.7 - GPL-2.0-or-later */
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <obs-module.h>
#include <media-io/video-scaler.h>
#include <util/bmem.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <wchar.h>

#define KB_MAGIC 0x374F424BU
#define KB_VERSION 1U
#define KB_HEADER 64U
#define KB_MAX_WIDTH 1920U
#define KB_MAX_HEIGHT 1080U
#define KB_CAPACITY (KB_MAX_WIDTH * KB_MAX_HEIGHT * 4U)
#define KB_MAP_SIZE (KB_HEADER + KB_CAPACITY)
#define KB_FRESH_MS 600ULL

struct kb_header {
    uint32_t magic, version, width, height, stride, bytes, sequence, flags;
    uint64_t timestamp, tick_ms, session;
    uint32_t reserved[2];
};
_Static_assert(sizeof(struct kb_header) == KB_HEADER, "IPC header layout");

struct kb_bridge {
    obs_source_t *source;
    HANDLE motor_job, motor_process;
    HANDLE owner, input_mapping, output_mapping, input_mutex, output_mutex;
    uint8_t *input, *output, *cached;
    video_scaler_t *to_bgra, *from_bgra;
    uint32_t width, height, sequence, last_output;
    enum video_format format;
    bool full_range, configured, direct, cache_valid, conversion_ok;
    float color_matrix[16];
    uint64_t session, cached_tick;
    volatile LONG enabled;
};

static bool kb_lock(HANDLE mutex)
{
    DWORD result = WaitForSingleObject(mutex, 0);
    return result == WAIT_OBJECT_0 || result == WAIT_ABANDONED;
}

static const char *kb_name(void *unused)
{
    UNUSED_PARAMETER(unused);
    return "KattBeauty - Maquillaje OBS";
}

static void kb_update(void *data, obs_data_t *settings)
{
    struct kb_bridge *b = data;
    InterlockedExchange(&b->enabled, obs_data_get_bool(settings, "apply") ? 1 : 0);
}

static void kb_defaults(obs_data_t *settings)
{
    obs_data_set_default_bool(settings, "apply", true);
}

static obs_properties_t *kb_properties(void *unused)
{
    UNUSED_PARAMETER(unused);
    obs_properties_t *p = obs_properties_create();
    obs_properties_add_bool(p, "apply", "Aplicar maquillaje del motor local");
    obs_properties_add_text(p, "instructions",
        "El motor arranca con este filtro. Ajusta el maquillaje en su ventana. "
        "Usa una sola instancia de este filtro, directamente en tu camara.", OBS_TEXT_INFO);
    return p;
}

static void kb_start_motor(struct kb_bridge *b)
{
    wchar_t base[32768], config[32768], python[32768], script[32768];
    DWORD count = GetEnvironmentVariableW(L"LOCALAPPDATA", base, 32768);
    if (!count || count > 32000) return;
    swprintf_s(config, 32768, L"%ls\\KattBeauty\\motor-path.txt", base);
    FILE *file = NULL;
    if (_wfopen_s(&file, config, L"rt, ccs=UTF-8") || !file) {
        blog(LOG_WARNING, "[KattBeauty] Falta instalar el arranque automatico.");
        return;
    }
    script[0] = 0;
    bool ok = fgetws(python, 32768, file) != NULL;
    if (ok) fgetws(script, 32768, file);
    fclose(file);
    if (!ok) return;
    python[wcscspn(python, L"\r\n")] = 0;
    script[wcscspn(script, L"\r\n")] = 0;
    if (wcschr(python, L'"') || wcschr(script, L'"')) return;
    wchar_t command[65536];
    if (script[0])
        swprintf_s(command, 65536, L"\"%ls\" -u \"%ls\"", python, script);
    else
        swprintf_s(command, 65536, L"\"%ls\"", python);
    STARTUPINFOW startup = {0}; startup.cb = sizeof(startup);
    PROCESS_INFORMATION process = {0};
    HANDLE job = CreateJobObjectW(NULL, NULL);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits = {0};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits))) {
        if (job) CloseHandle(job);
        return;
    }
    if (!CreateProcessW(python, command, NULL, NULL, FALSE,
            CREATE_NO_WINDOW | CREATE_SUSPENDED, NULL, NULL, &startup, &process)) {
        blog(LOG_ERROR, "[KattBeauty] No se pudo iniciar el motor: %lu", (unsigned long)GetLastError());
        CloseHandle(job); return;
    }
    if (!AssignProcessToJobObject(job, process.hProcess)) {
        TerminateProcess(process.hProcess, 1);
        CloseHandle(process.hThread); CloseHandle(process.hProcess); CloseHandle(job);
        return;
    }
    b->motor_job = job; b->motor_process = process.hProcess;
    ResumeThread(process.hThread); CloseHandle(process.hThread);
    blog(LOG_INFO, "[KattBeauty] Motor iniciado automaticamente.");
}

static void kb_destroy(void *data)
{
    struct kb_bridge *b = data;
    if (!b) return;
    if (b->motor_job) CloseHandle(b->motor_job);
    if (b->motor_process) CloseHandle(b->motor_process);
    video_scaler_destroy(b->to_bgra);
    video_scaler_destroy(b->from_bgra);
    bfree(b->cached);
    if (b->input) UnmapViewOfFile(b->input);
    if (b->output) UnmapViewOfFile(b->output);
    if (b->input_mapping) CloseHandle(b->input_mapping);
    if (b->output_mapping) CloseHandle(b->output_mapping);
    if (b->input_mutex) CloseHandle(b->input_mutex);
    if (b->output_mutex) CloseHandle(b->output_mutex);
    if (b->owner) CloseHandle(b->owner);
    bfree(b);
}

static void *kb_create(obs_data_t *settings, obs_source_t *source)
{
    struct kb_bridge *b = bzalloc(sizeof(*b));
    b->source = source;
    SetLastError(ERROR_SUCCESS);
    b->owner = CreateMutexW(NULL, FALSE, L"Local\\KattBeauty_OBS7_FilterOwner");
    DWORD owner_error = GetLastError();
    if (!b->owner || owner_error == ERROR_ALREADY_EXISTS) {
        blog(LOG_WARNING, "[KattBeauty OBS] Solo se admite una instancia del filtro de maquillaje.");
        kb_destroy(b);
        return NULL;
    }
    b->input_mutex = CreateMutexW(NULL, FALSE, L"Local\\KattBeauty_OBS7_InputLock");
    b->output_mutex = CreateMutexW(NULL, FALSE, L"Local\\KattBeauty_OBS7_OutputLock");
    b->input_mapping = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE,
        0, KB_MAP_SIZE, L"Local\\KattBeauty_OBS7_Input");
    b->output_mapping = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE,
        0, KB_MAP_SIZE, L"Local\\KattBeauty_OBS7_Output");
    if (b->input_mapping)
        b->input = MapViewOfFile(b->input_mapping, FILE_MAP_ALL_ACCESS, 0, 0, KB_MAP_SIZE);
    if (b->output_mapping)
        b->output = MapViewOfFile(b->output_mapping, FILE_MAP_ALL_ACCESS, 0, 0, KB_MAP_SIZE);
    if (!b->input_mutex || !b->output_mutex || !b->input || !b->output) {
        blog(LOG_ERROR, "[KattBeauty OBS] No se pudo crear el canal local (Windows %lu).",
            (unsigned long)GetLastError());
        kb_destroy(b);
        return NULL;
    }
    b->session = (GetTickCount64() << 20) ^ (uint64_t)(uintptr_t)b ^ GetCurrentProcessId();
    if (!b->session) b->session = 1;
    if (kb_lock(b->input_mutex)) {
        memset(b->input, 0, KB_HEADER);
        ReleaseMutex(b->input_mutex);
    }
    /* No se reinicia la salida: el motor puede haber arrancado primero.
       El identificador de sesion impide usar imagenes de una sesion anterior. */
    kb_update(b, settings);
    kb_start_motor(b);
    blog(LOG_INFO, "[KattBeauty OBS] Puente de maquillaje preparado.");
    return b;
}

static enum video_colorspace kb_colorspace(const struct obs_source_frame *frame)
{
    float matrix[16], lo[3], hi[3];
    double best = 1.0e100;
    enum video_colorspace selected = VIDEO_CS_709;
    enum video_range_type range = frame->full_range ? VIDEO_RANGE_FULL : VIDEO_RANGE_PARTIAL;
    const enum video_colorspace candidates[] = { VIDEO_CS_601, VIDEO_CS_709 };
    for (size_t c = 0; c < 2; ++c) {
        if (!video_format_get_parameters_for_format(candidates[c], range,
                frame->format, matrix, lo, hi)) continue;
        double error = 0;
        for (size_t i = 0; i < 16; ++i) {
            double delta = (double)frame->color_matrix[i] - matrix[i];
            error += delta * delta;
        }
        if (error < best) { best = error; selected = candidates[c]; }
    }
    return selected;
}

static bool kb_configure(struct kb_bridge *b, const struct obs_source_frame *frame)
{
    if (b->configured && b->width == frame->width && b->height == frame->height
        && b->format == frame->format && b->full_range == frame->full_range
        && memcmp(b->color_matrix, frame->color_matrix, sizeof(b->color_matrix)) == 0)
        return b->conversion_ok;

    video_scaler_destroy(b->to_bgra); b->to_bgra = NULL;
    video_scaler_destroy(b->from_bgra); b->from_bgra = NULL;
    bfree(b->cached); b->cached = NULL;
    b->cache_valid = false;
    b->last_output = 0;
    b->width = frame->width; b->height = frame->height;
    b->format = frame->format; b->full_range = frame->full_range;
    memcpy(b->color_matrix, frame->color_matrix, sizeof(b->color_matrix));
    b->configured = true;
    b->direct = frame->format == VIDEO_FORMAT_BGRA || frame->format == VIDEO_FORMAT_BGRX;
    size_t bytes = (size_t)b->width * b->height * 4;
    b->cached = bmalloc(bytes);
    b->conversion_ok = b->direct;
    if (!b->direct) {
        struct video_scale_info source = {
            .format = frame->format, .width = frame->width, .height = frame->height,
            .range = frame->full_range ? VIDEO_RANGE_FULL : VIDEO_RANGE_PARTIAL,
            .colorspace = kb_colorspace(frame),
        };
        struct video_scale_info dest = {
            .format = VIDEO_FORMAT_BGRA, .width = frame->width, .height = frame->height,
            .range = VIDEO_RANGE_FULL, .colorspace = VIDEO_CS_SRGB,
        };
        int first = video_scaler_create(&b->to_bgra, &dest, &source, VIDEO_SCALE_FAST_BILINEAR);
        int second = video_scaler_create(&b->from_bgra, &source, &dest, VIDEO_SCALE_FAST_BILINEAR);
        b->conversion_ok = first == VIDEO_SCALER_SUCCESS && second == VIDEO_SCALER_SUCCESS;
    }
    blog(b->conversion_ok ? LOG_INFO : LOG_WARNING,
        "[KattBeauty OBS] Camara %ux%u formato %d: conversion %s.",
        b->width, b->height, (int)b->format, b->conversion_ok ? "lista" : "no disponible");
    return b->conversion_ok;
}

static bool kb_output(struct kb_bridge *b, uint64_t now)
{
    bool alive = false;
    if (!kb_lock(b->output_mutex))
        return b->cache_valid && now >= b->cached_tick && now - b->cached_tick < KB_FRESH_MS;
    struct kb_header h;
    memcpy(&h, b->output, sizeof(h));
    alive = h.magic == KB_MAGIC && h.version == KB_VERSION
        && now >= h.tick_ms && now - h.tick_ms < KB_FRESH_MS;
    if (alive && b->configured && b->cached && h.session == b->session && h.sequence && h.sequence != b->last_output
        && h.width == b->width && h.height == b->height && h.stride == b->width * 4
        && h.bytes == b->width * b->height * 4 && h.bytes <= KB_CAPACITY) {
        memcpy(b->cached, b->output + KB_HEADER, h.bytes);
        b->cache_valid = true;
        b->last_output = h.sequence;
        b->cached_tick = h.tick_ms;
    }
    ReleaseMutex(b->output_mutex);
    return alive;
}

static struct obs_source_frame *kb_video(void *data, struct obs_source_frame *frame)
{
    struct kb_bridge *b = data;
    if (!frame || !InterlockedCompareExchange(&b->enabled, 0, 0)) return frame;
    if (!frame->width || !frame->height || frame->width > KB_MAX_WIDTH || frame->height > KB_MAX_HEIGHT)
        return frame;
    uint64_t now = GetTickCount64();
    /* Lee primero el latido; no convierte fotogramas si el motor esta cerrado. */
    if (!kb_output(b, now)) return frame;
    if (!kb_configure(b, frame)) return frame;
    uint32_t stride = b->width * 4;
    uint32_t bytes = stride * b->height;

    if (kb_lock(b->input_mutex)) {
        bool converted = true;
        if (b->direct) {
            for (uint32_t y = 0; y < b->height; ++y)
                memcpy(b->input + KB_HEADER + (size_t)y * stride,
                       frame->data[0] + (size_t)y * frame->linesize[0], stride);
        } else {
            uint8_t *out[MAX_AV_PLANES] = { b->input + KB_HEADER };
            uint32_t lines[MAX_AV_PLANES] = { stride };
            const uint8_t *input[MAX_AV_PLANES] = {0};
            for (size_t i = 0; i < MAX_AV_PLANES; ++i) input[i] = frame->data[i];
            converted = video_scaler_scale(b->to_bgra, out, lines, input, frame->linesize);
        }
        if (converted) {
            if (++b->sequence == 0) ++b->sequence;
            struct kb_header h = {
                .magic = KB_MAGIC, .version = KB_VERSION,
                .width = b->width, .height = b->height, .stride = stride,
                .bytes = bytes, .sequence = b->sequence,
                .flags = frame->flip ? 1U : 0U,
                .timestamp = frame->timestamp, .tick_ms = now, .session = b->session,
            };
            memcpy(b->input, &h, sizeof(h));
        }
        ReleaseMutex(b->input_mutex);
    }

    /* Vuelve a leer la salida tras configurar: evita conservar un tamano antiguo. */
    kb_output(b, now);
    if (!b->cache_valid || now < b->cached_tick || now - b->cached_tick >= KB_FRESH_MS)
        return frame;
    if (b->direct) {
        for (uint32_t y = 0; y < b->height; ++y)
            memcpy(frame->data[0] + (size_t)y * frame->linesize[0],
                   b->cached + (size_t)y * stride, stride);
    } else {
        const uint8_t *input[MAX_AV_PLANES] = { b->cached };
        uint32_t lines[MAX_AV_PLANES] = { stride };
        video_scaler_scale(b->from_bgra, frame->data, frame->linesize, input, lines);
    }
    return frame;
}

void kattbeauty_register_makeup(void)
{
    static struct obs_source_info info = {
        .id = "kattbeauty_makeup_bridge_v1",
        .type = OBS_SOURCE_TYPE_FILTER,
        .output_flags = OBS_SOURCE_VIDEO | OBS_SOURCE_ASYNC,
        .get_name = kb_name, .create = kb_create, .destroy = kb_destroy,
        .get_defaults = kb_defaults, .get_properties = kb_properties,
        .update = kb_update, .filter_video = kb_video,
    };
    obs_register_source(&info);
    blog(LOG_INFO, "[KattBeauty OBS] Filtro de maquillaje registrado.");
}
