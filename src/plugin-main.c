/* KattBeauty Studio - SPDX-License-Identifier: GPL-2.0-or-later */
#include <obs-module.h>
#include <graphics/vec2.h>
#include <util/bmem.h>
#include <plugin-support.h>
OBS_DECLARE_MODULE()
void kattbeauty_register_makeup(void);
static const char *beauty_shader =
    "uniform float4x4 ViewProj;\n"
    "uniform texture2d image;\n"
    "uniform float2 pixel_step;\n"
    "uniform float softness;\n"
    "uniform float brightness;\n"
    "uniform float contrast;\n"
    "uniform float saturation;\n"
    "sampler_state linear_sampler { Filter = Linear; AddressU = Clamp; AddressV = Clamp; };\n"
    "struct VertData { float4 pos : POSITION; float2 uv : TEXCOORD0; };\n"
    "VertData VSBeauty(VertData v) { VertData o; o.pos = mul(float4(v.pos.xyz, 1.0), ViewProj); o.uv=v.uv; return o; }\n"
    "float4 PSBeauty(VertData v) : TARGET {\n"
    " float4 original=image.Sample(linear_sampler,v.uv);\n"
    " float3 total=original.rgb; float weight_sum=1.0;\n"
    " for(int y=-2;y<=2;y++) { for(int x=-2;x<=2;x++) {\n"
    "  float2 offset=float2(x,y)*pixel_step;\n"
    "  float4 sample_color=image.Sample(linear_sampler,v.uv+offset);\n"
    "  float3 delta=sample_color.rgb-original.rgb;\n"
    "  float spatial=exp(-0.35*float(x*x+y*y));\n"
    "  float range_weight=exp(-dot(delta,delta)*60.0);\n"
    "  float alpha_weight=saturate(sample_color.a*100.0);\n"
    "  float weight=spatial*range_weight*alpha_weight;\n"
    "  total+=sample_color.rgb*weight; weight_sum+=weight;\n"
    " } }\n"
    " float3 color=lerp(original.rgb,total/weight_sum,softness);\n"
    " color=(color-0.5)*contrast+0.5+brightness;\n"
    " float luminance=dot(color,float3(0.2126,0.7152,0.0722));\n"
    " color=lerp(float3(luminance,luminance,luminance),color,saturation);\n"
    " return float4(saturate(color),original.a);\n"
    "}\n"
    "technique Draw { pass { vertex_shader=VSBeauty(v); pixel_shader=PSBeauty(v); } }\n"
;
struct beauty_filter {
 obs_source_t *source; gs_effect_t *effect;
 gs_eparam_t *pixel_step, *softness, *brightness, *contrast, *saturation;
 float soft,bright,cont,sat,radius;
};
static const char *beauty_name(void *unused) { UNUSED_PARAMETER(unused); return "KattBeauty Studio - Belleza"; }
static void beauty_defaults(obs_data_t *s) {
 obs_data_set_default_double(s,"softness",35.0);
 obs_data_set_default_double(s,"radius",2.0);
 obs_data_set_default_double(s,"brightness",0.0);
 obs_data_set_default_double(s,"contrast",100.0);
 obs_data_set_default_double(s,"saturation",100.0);
}
static void beauty_update(void *data, obs_data_t *s) {
 struct beauty_filter *f=data;
 f->soft=(float)obs_data_get_double(s,"softness")/100.0f;
 f->radius=(float)obs_data_get_double(s,"radius");
 f->bright=(float)obs_data_get_double(s,"brightness")/100.0f;
 f->cont=(float)obs_data_get_double(s,"contrast")/100.0f;
 f->sat=(float)obs_data_get_double(s,"saturation")/100.0f;
}
static obs_properties_t *beauty_properties(void *unused) {
 UNUSED_PARAMETER(unused); obs_properties_t *p=obs_properties_create();
 obs_properties_add_float_slider(p,"softness","Suavizado (%)",0,100,1);
 obs_properties_add_float_slider(p,"radius","Radio del suavizado",1,4,.1);
 obs_properties_add_float_slider(p,"brightness","Brillo",-20,20,1);
 obs_properties_add_float_slider(p,"contrast","Contraste (%)",70,130,1);
 obs_properties_add_float_slider(p,"saturation","Saturacion (%)",0,150,1);
 return p;
}
static void beauty_destroy(void *data) {
 struct beauty_filter *f=data; if(!f)return;
 obs_enter_graphics(); if(f->effect)gs_effect_destroy(f->effect); obs_leave_graphics(); bfree(f);
}
static void *beauty_create(obs_data_t *s, obs_source_t *source) {
 struct beauty_filter *f=bzalloc(sizeof(*f)); char *errors=NULL; f->source=source;
 obs_enter_graphics(); f->effect=gs_effect_create(beauty_shader,"kattbeauty-inline.effect",&errors);
 if(f->effect) {
  f->pixel_step=gs_effect_get_param_by_name(f->effect,"pixel_step");
  f->softness=gs_effect_get_param_by_name(f->effect,"softness");
  f->brightness=gs_effect_get_param_by_name(f->effect,"brightness");
  f->contrast=gs_effect_get_param_by_name(f->effect,"contrast");
  f->saturation=gs_effect_get_param_by_name(f->effect,"saturation");
 }
 obs_leave_graphics();
 if(errors){blog(LOG_WARNING,"[KattBeauty] Shader: %s",errors);bfree(errors);}
 if(!f->effect||!f->pixel_step||!f->softness||!f->brightness||!f->contrast||!f->saturation){beauty_destroy(f);return NULL;}
 beauty_update(f,s); return f;
}
static void beauty_render(void *data,gs_effect_t *unused) {
 UNUSED_PARAMETER(unused); struct beauty_filter *f=data;
 obs_source_t *target=obs_filter_get_target(f->source);
 if(!target||!f->effect){obs_source_skip_video_filter(f->source);return;}
 uint32_t width=obs_source_get_base_width(target),height=obs_source_get_base_height(target);
 if(!width||!height){obs_source_skip_video_filter(f->source);return;}
 if(!obs_source_process_filter_begin(f->source,GS_RGBA,OBS_NO_DIRECT_RENDERING))return;
 struct vec2 step;vec2_set(&step,f->radius/(float)width,f->radius/(float)height);
 gs_effect_set_vec2(f->pixel_step,&step);gs_effect_set_float(f->softness,f->soft);
 gs_effect_set_float(f->brightness,f->bright);gs_effect_set_float(f->contrast,f->cont);
 gs_effect_set_float(f->saturation,f->sat);
 obs_source_process_filter_end(f->source,f->effect,width,height);
}
static struct obs_source_info beauty_info={
 .id="kattbeauty_studio_filter",.type=OBS_SOURCE_TYPE_FILTER,.output_flags=OBS_SOURCE_VIDEO,
 .get_name=beauty_name,.create=beauty_create,.destroy=beauty_destroy,
 .get_defaults=beauty_defaults,.get_properties=beauty_properties,.update=beauty_update,.video_render=beauty_render,
};
bool obs_module_load(void) {
 obs_register_source(&beauty_info);kattbeauty_register_makeup();
 blog(LOG_INFO,"[KattBeauty] Studio 0.20.0 cargado.");return true;
}
void obs_module_unload(void) { blog(LOG_INFO,"[KattBeauty] Complemento descargado."); }
