from pathlib import Path
import importlib.util
import sys
import tempfile
import types
import json
import os
import unittest
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'motor'))
import kattbeauty_motor_obs as engine
import kattbeauty_panel as panel


def face():
    p=np.tile(np.array([115,80],np.float32),(478,1))
    p[10]=[115,12];p[152]=[115,143];p[234]=[26,76];p[454]=[204,76]
    for k,eye in enumerate(engine.EYES):
        cx,cy=64+k*102,49;direction=1 if k==0 else -1
        for idx,t in zip(eye['contour'],np.linspace(0,2*np.pi,16,endpoint=False)):p[idx]=[cx-direction*20*np.cos(t),cy+8*np.sin(t)]
        for idx,t in zip(eye['upper'],np.linspace(0,np.pi,9)):p[idx]=[cx-direction*20*np.cos(t),cy-8*np.sin(t)]
        p[eye['lids'][0]]=[cx,41];p[eye['lids'][1]]=[cx,57];p[eye['center']]=[cx,cy]
        for idx,t in zip(eye['iris'],np.linspace(0,2*np.pi,4,endpoint=False)):p[idx]=[cx+8*np.cos(t),cy+8*np.sin(t)]
    for idx,pos in {168:(115,52),6:(115,77),1:(115,96),98:(101,99),327:(129,99)}.items():p[idx]=pos
    outer=[61,185,40,39,37,0,267,269,270,409,291,375,321,405,314,17,84,181,91,146]
    inner=[78,191,80,81,82,13,312,311,310,415,308,324,318,402,317,14,87,178,88,95]
    for ids,a,b in [(outer,24,8),(inner,17,3)]:
        for idx,t in zip(ids,np.linspace(0,2*np.pi,len(ids),endpoint=False)):p[idx]=[115+a*np.cos(t),119+b*np.sin(t)]
    return p


class CompleteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=face()
        y,x=np.mgrid[:160,:230]
        cls.frame=np.stack([(80+x%35),(105+y%40),(145+x%40)],axis=2).astype(np.uint8)
        cls.textures={i:engine.make_lash_texture(i) for i in range(1,7)}

    def test_all_styles_render(self):
        count=0
        for color in range(1,10):
            for liner in range(1,8):
                for lash in range(7):
                    settings=dict(engine.DEFAULTS,color=color,liner=liner,lash=lash,blush=True)
                    out=engine.render(self.frame,self.p,settings,self.textures)
                    self.assertEqual(out.shape,self.frame.shape);self.assertEqual(out.dtype,np.uint8);count+=1
        self.assertEqual(count,441)

    def test_uniform_face_scaling(self):
        p=self.p.copy()
        maps=engine.face_remap_coordinates(self.frame.shape[:2],p,.8)
        x0,y0,x1,y1,mx,my=maps
        x=155
        displacements=[float(mx[y-y0,x-x0]-(x-x0)) for y in (18,76,137)]
        self.assertLess(max(displacements)-min(displacements),.001)
        self.assertGreater(displacements[0],0)

    def test_liner_can_move_down(self):
        white=np.full_like(self.frame,220)
        base=dict(engine.DEFAULTS,liner=1,ink=1.,width=1.,liner_offset=-.03)
        upper=engine.apply_liner(white,self.p,base)
        lower=engine.apply_liner(white,self.p,dict(base,liner_offset=.08))
        ya=np.where(np.any(upper<170,axis=2))[0].mean()
        yb=np.where(np.any(lower<170,axis=2))[0].mean()
        self.assertGreater(yb,ya+2)

    def test_nose_shape_bypass_and_profile(self):
        none=dict(engine.DEFAULTS,nose_width=0.,nose_profile=0.,tip_lift=0.)
        np.testing.assert_array_equal(engine.nose_shape(self.frame,self.p,none),self.frame)
        p=self.p.copy();p[1,0]+=20
        out=engine.nose_shape(self.frame,p,dict(none,nose_profile=.7))
        self.assertTrue(np.any(out!=self.frame));np.testing.assert_array_equal(out[:15],self.frame[:15])

    def test_no_effects_is_identity(self):
        off=dict(engine.DEFAULTS,color=0,liner=0,lash=0,shadow=False,blush=False,lips=False,
                 slim=0.,nose=0.,nose_width=0.,nose_profile=0.,tip_lift=0.)
        np.testing.assert_array_equal(engine.render(self.frame,self.p,off,self.textures),self.frame)

    def test_invalid_settings_and_new_limits(self):
        settings=engine.normalize_settings(dict(lash=6,color=9,liner=7,slim=float('nan'),nose_profile=5.,liner_offset=-8.))
        self.assertEqual(settings['lash'],6);self.assertEqual(settings['color'],9)
        self.assertEqual(settings['nose_profile'],1.);self.assertEqual(settings['liner_offset'],-.06)
        self.assertEqual(settings['slim'],engine.DEFAULTS['slim'])

    def test_variants_are_distinct_and_premultiplied(self):
        for i,original in [(4,2),(5,1),(6,3)]:
            a,b=self.textures[i],self.textures[original]
            self.assertFalse(np.array_equal(a,b))
            self.assertTrue(np.isfinite(a).all());self.assertGreaterEqual(a.min(),0);self.assertLessEqual(a.max(),1)
            self.assertTrue((a[:,:,:3]<=a[:,:,3:4]+.001).all())

    def test_latest_queue_and_snapshot(self):
        state=panel.SharedState(engine.DEFAULTS)
        for i in range(50):state.latest(state.frames,i)
        self.assertEqual(state.frames.qsize(),1);self.assertEqual(state.frames.get_nowait(),49)
        settings,_,_=state.snapshot();settings['slim']=1.
        self.assertNotEqual(settings['slim'],state.settings['slim'])

    def test_launcher_can_run_panel_through_runpy(self):
        import runpy
        seen=[]
        fake=types.SimpleNamespace(launch=lambda e:seen.append(e) or 0)
        with patch.dict(sys.modules,{'kattbeauty_panel':fake}):
            with self.assertRaises(SystemExit) as exited:
                runpy.run_path(str(ROOT/'motor/kattbeauty_motor_obs.py'),run_name='__main__')
        self.assertEqual(exited.exception.code,0)
        self.assertIn('nose_profile',seen[0].DEFAULTS)
        self.assertTrue(callable(seen[0].render))

    def test_worker_publishes_without_ui(self):
        state=panel.SharedState(engine.DEFAULTS)
        state.compare=True
        frames=[]
        class Camera:
            count=0
            closed=False
            def read(inner):
                inner.count+=1
                if inner.count>2:
                    state.stop.set();return True,None
                return True,self.frame.copy()
            def publish(inner,frame):frames.append(frame.copy())
            def close(inner):inner.closed=True
        class Mesh:
            def __init__(inner,**kwargs):pass
            def __enter__(inner):return inner
            def __exit__(inner,*args):pass
            def process(inner,rgb):return types.SimpleNamespace(multi_face_landmarks=None)
        camera=Camera()
        modules={'mediapipe':types.SimpleNamespace(solutions=types.SimpleNamespace(face_mesh=types.SimpleNamespace(FaceMesh=Mesh))),
                 'kb_obs_transport':types.SimpleNamespace(ObsCamera=lambda:camera)}
        with patch.dict(sys.modules,modules),patch.object(engine,'make_lash_texture',return_value=None):
            panel.process_video(engine,state)
        self.assertEqual(len(frames),2)
        for frame in frames:np.testing.assert_array_equal(frame,self.frame)
        self.assertTrue(camera.closed)
        self.assertLessEqual(state.frames.qsize(),1)



if __name__=='__main__':unittest.main(verbosity=2)
