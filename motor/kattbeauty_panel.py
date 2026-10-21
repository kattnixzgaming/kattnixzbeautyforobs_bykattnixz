"""Panel local para KattBeauty: interfaz en el hilo principal, video en un trabajador."""
import base64
import json
import queue
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class SharedState:
    def __init__(self, settings):
        self.lock=threading.Lock()
        self.settings=dict(settings)
        self.compare=False
        self.preview=True
        self.stop=threading.Event()
        self.frames=queue.Queue(maxsize=1)
        self.status=queue.Queue(maxsize=1)

    def snapshot(self):
        with self.lock:
            return dict(self.settings),self.compare,self.preview

    @staticmethod
    def latest(channel, value):
        try:channel.put_nowait(value)
        except queue.Full:
            try:channel.get_nowait()
            except queue.Empty:pass
            try:channel.put_nowait(value)
            except queue.Full:pass


def process_video(engine, state):
    reader=None
    try:
        import mediapipe as mp
        from kb_obs_transport import ObsCamera
        np,cv2=engine.np,engine.cv2
        cv2.setNumThreads(1)
        reader=ObsCamera()
        textures={i:engine.make_lash_texture(i) for i in range(1,7)}
        smooth=None
        last_received=last_preview=0.
        last_frame=time.perf_counter()
        fps=0.
        with mp.solutions.face_mesh.FaceMesh(static_image_mode=False,max_num_faces=1,
                refine_landmarks=True,min_detection_confidence=.5,min_tracking_confidence=.5) as mesh:
            while not state.stop.is_set():
                ok,frame=reader.read()
                now=time.monotonic()
                if not ok:raise RuntimeError('Se interrumpio el canal de OBS.')
                if frame is None:
                    if now-last_received>1:
                        state.latest(state.status,('waiting',fps,'Esperando la camara de OBS'))
                    continue
                if now-last_received>.6:smooth=None
                last_received=now
                h,w=frame.shape[:2]
                dw=min(480,w)
                small=cv2.resize(frame,(dw,max(1,round(h*dw/w))))
                rgb=cv2.cvtColor(small,cv2.COLOR_BGR2RGB);rgb.flags.writeable=False
                result=mesh.process(rgb)
                points=None
                if result.multi_face_landmarks:
                    raw=np.array([(p.x*w,p.y*h) for p in result.multi_face_landmarks[0].landmark],np.float32)
                    if smooth is None or smooth.shape!=raw.shape:smooth=raw
                    else:
                        movement=float(np.median(np.linalg.norm(raw-smooth,axis=1)))
                        weight=.82 if movement>w*.007 else .68
                        smooth=smooth*(1-weight)+raw*weight
                    points=smooth.copy()
                    responsive=set(range(468,478))
                    for eye in engine.EYES:responsive.update(eye['contour'])
                    indices=list(responsive);points[indices]=raw[indices]
                else:smooth=None
                settings,compare,preview=state.snapshot()
                output=frame.copy() if compare or points is None else engine.render(frame,points,settings,textures)
                reader.publish(output)
                clock=time.perf_counter()
                current=1/max(clock-last_frame,.001)
                fps=current if not fps else fps*.9+current*.1
                last_frame=clock
                if preview and now-last_preview>.10:
                    state.latest(state.frames,output)
                    last_preview=now
                state.latest(state.status,('ok' if points is not None else 'face',fps,
                    'Original en OBS' if compare else ('Maquillaje activo' if points is not None else 'Buscando rostro')))
    except Exception as error:
        traceback.print_exc()
        state.latest(state.status,('error',0,str(error)))
    finally:
        if reader is not None:reader.close()


class Panel:
    BG='#12111b'; CARD='#1d1a2b'; TEXT='#eee9fa'; MUTED='#b9b0ca'; ACCENT='#c0a0ff'
    def __init__(self, engine, start_worker=True):
        self.engine=engine
        self.state=SharedState(engine.load_settings())
        self.root=tk.Tk()
        self.root.title('KattBeauty Studio · Panel de maquillaje')
        self.root.geometry('1160x760');self.root.minsize(940,640)
        self.root.configure(bg=self.BG)
        style=ttk.Style(self.root);style.theme_use('clam')
        style.configure('.',font=('Segoe UI',10),background=self.CARD,foreground=self.TEXT)
        style.configure('TFrame',background=self.CARD)
        style.configure('TLabel',background=self.CARD,foreground=self.TEXT)
        style.configure('TButton',padding=(10,7),background='#332942',foreground=self.TEXT)
        style.map('TButton',background=[('active','#514064')])
        style.configure('TNotebook',background=self.BG,borderwidth=0)
        style.configure('TNotebook.Tab',padding=(11,10),background='#292336',foreground=self.MUTED)
        style.map('TNotebook.Tab',background=[('selected','#4b3768')],foreground=[('selected','white')])
        style.configure('TCheckbutton',background=self.CARD,foreground=self.TEXT)
        style.configure('TCombobox',fieldbackground='#312b42',foreground='white',padding=6)
        style.map('TCombobox',fieldbackground=[('readonly','#312b42')],foreground=[('readonly','white')])
        style.configure('TLabelframe',background=self.CARD,foreground=self.TEXT)
        style.configure('TLabelframe.Label',background=self.CARD,foreground=self.ACCENT)
        self.variables={};self.syncing=False;self.save_job=None
        top=tk.Frame(self.root,bg=self.BG);top.pack(fill='x',padx=20,pady=(17,12))
        tk.Label(top,text='KattBeauty Studio',font=('Segoe UI',21,'bold'),fg=self.TEXT,bg=self.BG).pack(side='left')
        tk.Label(top,text='TU MAQUILLAJE · EN OBS',font=('Segoe UI',9),fg=self.ACCENT,bg=self.BG).pack(side='right')
        content=tk.Frame(self.root,bg=self.BG);content.pack(fill='both',expand=True,padx=16)
        left=tk.Frame(content,bg=self.CARD);left.pack(side='left',fill='both',expand=True,padx=(0,12))
        self.preview_label=tk.Label(left,text='Preparando motor…\n\nLa camara permanece abierta en OBS.',
            fg=self.MUTED,bg='#090910',font=('Segoe UI',13))
        self.preview_label.pack(fill='both',expand=True,padx=10,pady=10)
        self.status_text=tk.StringVar(value='Cargando seguimiento facial…')
        tk.Label(left,textvariable=self.status_text,bg=self.CARD,fg=self.ACCENT,font=('Segoe UI',11),anchor='w').pack(fill='x',padx=14,pady=(0,8))
        tk.Label(left,text='La vista previa no agrega textos al stream.',fg=self.MUTED,bg=self.CARD,anchor='w').pack(fill='x',padx=14,pady=(0,12))
        buttons=ttk.Frame(left);buttons.pack(fill='x',padx=12,pady=(0,10))
        self.compare_text=tk.StringVar(value='Comparar con original')
        ttk.Button(buttons,textvariable=self.compare_text,command=self.toggle_compare).pack(side='left',padx=(0,6))
        self.preview_var=tk.BooleanVar(value=True)
        ttk.Checkbutton(buttons,text='Vista previa',variable=self.preview_var,command=self.toggle_preview).pack(side='left')
        right=tk.Frame(content,bg=self.CARD,width=470);right.pack(side='right',fill='both');right.pack_propagate(False)
        notebook=ttk.Notebook(right);notebook.pack(fill='both',expand=True,padx=8,pady=8)
        tabs={}
        canvases=[]
        for title in ['Rostro','Nariz','Ojos','Delineado','Pestañas']:
            page=ttk.Frame(notebook);notebook.add(page,text=title)
            canvas=tk.Canvas(page,bg=self.CARD,highlightthickness=0)
            scrollbar=ttk.Scrollbar(page,orient='vertical',command=canvas.yview)
            scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
            canvas.configure(yscrollcommand=scrollbar.set)
            tab=ttk.Frame(canvas)
            window=canvas.create_window((0,0),window=tab,anchor='nw')
            tab.bind('<Configure>',lambda event,c=canvas:c.configure(scrollregion=c.bbox('all')))
            canvas.bind('<Configure>',lambda event,c=canvas,w=window:c.itemconfigure(w,width=event.width))
            tabs[title]=tab;canvases.append(canvas)
        def wheel(event):
            if event.x_root>=right.winfo_rootx():
                canvases[notebook.index(notebook.select())].yview_scroll(-int(event.delta/120),'units')
        self.root.bind('<MouseWheel>',wheel)
        self.note(tabs['Rostro'],'Afinado parejo de frente, pomulos y mandibula.\nEl cambio tambien estrecha suavemente los ojos.\nSuavizado: ajustalo en el filtro Belleza de OBS.')
        self.slider(tabs['Rostro'],'slim','Afinado uniforme',0,100)
        self.check(tabs['Rostro'],'shadow','Sombra de ojos')
        self.check(tabs['Rostro'],'blush','Rubor suave')
        self.slider(tabs['Rostro'],'makeup','Intensidad de sombra y rubor',0,100)
        self.check(tabs['Rostro'],'lips','Labios carmesi')
        self.slider(tabs['Rostro'],'lip_ink','Intensidad de labios',0,100)
        self.note(tabs['Nariz'],'Forma y maquillaje son controles separados.\nEmpieza con cantidades bajas al girar de lado.')
        self.slider(tabs['Nariz'],'nose_profile','Suavizar proyeccion de perfil',0,100)
        self.slider(tabs['Nariz'],'nose_width','Afinar alas y punta',0,100)
        self.slider(tabs['Nariz'],'tip_lift','Elevar punta',0,100)
        self.slider(tabs['Nariz'],'nose','Contorno con sombra y luz',0,100)
        self.note(tabs['Nariz'],'Ajuste visual 2D; no reconstruye una nariz 3D.\nEn perfiles extremos puede perder precision.')
        self.combo(tabs['Ojos'],'color','Pupilentes',{0:'Sin pupilentes',**{i:name for i,(name,_) in engine.COLORS.items()}})
        self.slider(tabs['Ojos'],'eye','Intensidad de pupilentes',0,100)
        self.note(tabs['Ojos'],'Se mantienen pupila y reflejos. Los colores\ndependen de tu iris y de la iluminacion.')
        self.combo(tabs['Delineado'],'liner','Estilo',{0:'Sin delineado',**{i:name for i,name in engine.LINERS.items() if i}})
        self.slider(tabs['Delineado'],'ink','Intensidad',0,100)
        self.slider(tabs['Delineado'],'width','Grosor',40,300)
        self.slider(tabs['Delineado'],'liner_offset','Bajar delineado (+) / subir (-)',-6,10)
        self.slider(tabs['Delineado'],'wing_lift','Altura de la colita (- baja / + sube)',-12,12)
        self.slider(tabs['Delineado'],'wing_length','Largo de la colita',60,150)
        self.slider(tabs['Delineado'],'liner_left','Ajuste extra: ojo 1',-5,5)
        self.slider(tabs['Delineado'],'liner_right','Ajuste extra: ojo 2',-5,5)
        self.combo(tabs['Pestañas'],'lash','Estilo de pestanas',engine.LASHES)
        self.slider(tabs['Pestañas'],'lash_ink','Intensidad',0,100)
        self.slider(tabs['Pestañas'],'length','Largo',40,200)
        self.note(tabs['Pestañas'],'Tres texturas originales y tres variantes:\nFoxy suave, Wispy densa y Volumen suave.\nEl delineado se aplica debajo de las pestanas.')
        footer=tk.Frame(self.root,bg=self.BG);footer.pack(fill='x',padx=18,pady=12)
        for title,callback in [('Natural',lambda:self.preset('Natural')),('Stream',lambda:self.preset('Stream')),
            ('Glam',lambda:self.preset('Glam')),('Guardar perfil',self.save_profile),('Cargar perfil',self.load_profile),
            ('Restablecer',self.reset),('Minimizar',self.root.iconify)]:
            ttk.Button(footer,text=title,command=callback).pack(side='left',padx=(0,6))
        self.saved_text=tk.StringVar(value='Cambios guardados automaticamente · X minimiza el panel')
        tk.Label(self.root,textvariable=self.saved_text,bg=self.BG,fg=self.MUTED,anchor='w').pack(fill='x',padx=20,pady=(0,10))
        self.root.protocol('WM_DELETE_WINDOW',self.root.iconify)
        menu=tk.Menu(self.root,tearoff=False)
        menu.add_command(label='Cerrar motor (OBS queda sin maquillaje)',command=self.close)
        self.root.config(menu=menu)
        self.worker=None
        if start_worker:
            self.worker=threading.Thread(target=process_video,args=(engine,self.state),daemon=True)
            self.worker.start()
        self.root.after(80,self.refresh)

    def note(self,parent,text):
        ttk.Label(parent,text=text,foreground=self.MUTED,wraplength=420,justify='left').pack(fill='x',padx=14,pady=(12,8))

    def slider(self,parent,key,label,low,high):
        holder=ttk.Frame(parent);holder.pack(fill='x',padx=14,pady=7)
        row=ttk.Frame(holder);row.pack(fill='x')
        ttk.Label(row,text=label).pack(side='left')
        value=tk.DoubleVar(value=self.state.settings[key]*100)
        display=tk.StringVar()
        ttk.Label(row,textvariable=display,foreground=self.ACCENT).pack(side='right')
        def changed(*args):
            display.set(f'{value.get():.0f}%')
            self.changed(key,value.get()/100.)
        value.trace_add('write',changed)
        ttk.Scale(holder,from_=low,to=high,variable=value).pack(fill='x',pady=(5,0))
        display.set(f'{value.get():.0f}%')
        self.variables[key]=value

    def combo(self,parent,key,label,choices):
        holder=ttk.Frame(parent);holder.pack(fill='x',padx=14,pady=12)
        ttk.Label(holder,text=label).pack(anchor='w',pady=(0,5))
        ids=list(choices);names=[choices[i] for i in ids]
        var=tk.StringVar(value=choices[self.state.settings[key]])
        combo=ttk.Combobox(holder,textvariable=var,values=names,state='readonly');combo.pack(fill='x')
        combo.bind('<<ComboboxSelected>>',lambda event:self.changed(key,ids[combo.current()]))
        self.variables[key]=(var,choices)

    def check(self,parent,key,label):
        var=tk.BooleanVar(value=self.state.settings[key])
        ttk.Checkbutton(parent,text=label,variable=var,command=lambda:self.changed(key,var.get())).pack(anchor='w',padx=14,pady=7)
        self.variables[key]=var

    def changed(self,key,value):
        if self.syncing:return
        with self.state.lock:
            settings=dict(self.state.settings);settings[key]=value
            self.state.settings=self.engine.normalize_settings(settings)
        if self.save_job:self.root.after_cancel(self.save_job)
        self.save_job=self.root.after(250,self.persist)

    def persist(self):
        self.save_job=None
        ok=self.engine.save_settings(self.state.snapshot()[0])
        self.saved_text.set('Guardado · X minimiza el panel' if ok else 'No se pudieron guardar los ajustes; consulta el registro.')

    def replace(self,settings):
        normalized=self.engine.normalize_settings(settings)
        with self.state.lock:self.state.settings=normalized
        self.syncing=True
        for key,var in self.variables.items():
            if isinstance(var,tuple):var[0].set(var[1][normalized[key]])
            elif isinstance(var,tk.BooleanVar):var.set(normalized[key])
            else:var.set(normalized[key]*100)
        self.syncing=False
        self.persist()

    def preset(self,name):
        settings=self.state.snapshot()[0]
        if name=='Natural':settings.update(eye=.25,ink=.40,width=.9,lash=4,lash_ink=.55,length=.9,slim=.15,nose=.18,nose_profile=.15,nose_width=.10,tip_lift=0,lip_ink=.35,makeup=.22)
        elif name=='Stream':settings.update(eye=.35,ink=.60,width=1.2,lash=2,lash_ink=.70,length=1.,slim=.20,nose=.25,nose_profile=.20,nose_width=.15,tip_lift=.10,lip_ink=.50,makeup=.35)
        else:settings.update(eye=.45,ink=.75,width=1.5,lash=6,lash_ink=.80,length=1.15,slim=.25,nose=.35,nose_profile=.25,nose_width=.20,tip_lift=.15,lip_ink=.65,makeup=.45)
        self.replace(settings)

    def reset(self):
        if messagebox.askyesno('Restablecer','¿Restablecer todos los ajustes?',parent=self.root):self.replace(self.engine.DEFAULTS)

    def save_profile(self):
        path=filedialog.asksaveasfilename(parent=self.root,title='Guardar perfil',defaultextension='.json',filetypes=[('Perfil KattBeauty','*.json')])
        if path:
            try:
                with open(path,'w',encoding='utf-8') as stream:json.dump(self.state.snapshot()[0],stream,indent=2)
            except OSError as error:messagebox.showerror('Guardar perfil',str(error),parent=self.root)

    def load_profile(self):
        path=filedialog.askopenfilename(parent=self.root,title='Cargar perfil',filetypes=[('Perfil KattBeauty','*.json')])
        if path:
            try:
                with open(path,encoding='utf-8-sig') as stream:saved=json.load(stream)
                if not isinstance(saved,dict):raise ValueError('El perfil debe contener ajustes de KattBeauty.')
                self.replace(saved)
            except (OSError,ValueError,TypeError) as error:messagebox.showerror('Cargar perfil',str(error),parent=self.root)

    def toggle_compare(self):
        with self.state.lock:
            self.state.compare=not self.state.compare
            compare=self.state.compare
        self.compare_text.set('Volver al maquillaje' if compare else 'Comparar con original')
        self.saved_text.set('Comparacion activa: OBS recibe el original' if compare else 'OBS recibe el maquillaje')

    def toggle_preview(self):
        with self.state.lock:self.state.preview=self.preview_var.get()
        if not self.preview_var.get():self.preview_label.config(image='',text='Vista previa pausada\nEl maquillaje sigue activo en OBS.')

    def refresh(self):
        if self.state.stop.is_set():return
        try:
            code,fps,status=self.state.status.get_nowait()
            self.status_text.set(f'{status} · {fps:.0f} FPS')
            if code=='error':self.saved_text.set('Error del motor. Revisa logs/motor-obs.log y reinicia OBS despues de corregirlo.')
        except queue.Empty:pass
        try:
            frame=self.state.frames.get_nowait()
            if self.preview_var.get():
                h,w=frame.shape[:2]
                scale=min(max(200,self.preview_label.winfo_width()-16)/w,max(160,self.preview_label.winfo_height()-16)/h,1.)
                preview=self.engine.cv2.resize(frame,(max(1,round(w*scale)),max(1,round(h*scale))))
                ok,png=self.engine.cv2.imencode('.png',preview,[self.engine.cv2.IMWRITE_PNG_COMPRESSION,1])
                if ok:
                    self.photo=tk.PhotoImage(data=base64.b64encode(png.tobytes()))
                    self.preview_label.config(image=self.photo,text='')
        except queue.Empty:pass
        self.root.after(80,self.refresh)

    def close(self):
        if messagebox.askyesno('Cerrar motor','¿Cerrar el motor? OBS mostrara el video sin maquillaje. Para volver a iniciarlo, reinicia OBS.',parent=self.root):
            self.state.stop.set();self.persist();self.root.destroy()

    def run(self):
        try:self.root.mainloop()
        finally:
            self.state.stop.set()
            self.engine.save_settings(self.state.snapshot()[0])
        return 0


def launch(engine):
    return Panel(engine).run()
