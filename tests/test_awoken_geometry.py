"""Geometry contracts for the video-directed Awoken stone profiles."""

import unittest

from bspharness import Map, box
from bspharness.geometry import dot, normalize, vector
from bspharness.kits import prism
from maps.awoken.geometry import Solids, cornice, ease, profiles


def inside(brush, point):
    return all(dot(normalize(f.normal),vector(point,f.points[1])) <= 0.0001
               for f in brush.faces)


class AwokenProfileTests(unittest.TestCase):
    def test_bevel_removes_exposed_corners_and_retains_face_centers(self):
        original=box(1000,1000,-600,1064,1064,-400,texture="aw_stone")
        refined,edges=ease(original,Solids([original]))
        self.assertTrue(edges)
        self.assertTrue(all(inside(original,p) for p in refined.vertices))
        self.assertFalse(inside(refined,(1000,1000,-500)))
        for p in ((1000,1032,-500),(1064,1032,-500),(1032,1000,-500),
                  (1032,1064,-500),(1032,1032,-600),(1032,1032,-400)):
            self.assertTrue(inside(refined,p))

    def test_shared_wall_joint_and_small_grate_bar_are_preserved(self):
        a=box(1000,1000,-600,1064,1064,-400,texture="aw_stone")
        b=box(1064,1000,-600,1128,1064,-400,texture="aw_stone")
        refined,edges=ease(a,Solids([a,b]))
        self.assertTrue(inside(refined,(1064,1000,-500)))
        self.assertFalse(any(all(p[0]==1064 for p in (e["start"],e["end"])) for e in edges))
        bar=box(1000,1000,-500,1004,1016,-300,texture="aw_trim")
        same,edges=ease(bar,Solids([bar]))
        self.assertIs(same,bar)
        self.assertFalse(edges)

    def test_cornice_is_continuous_and_keeps_its_rear_seal(self):
        original=box(1000,1000,-320,1064,1512,-192,texture="aw_trim")
        wall=box(1064,1000,-400,1100,1512,-160,texture="aw_stone")
        pieces,faces=cornice(original,Solids([original,wall]))
        self.assertTrue(faces)
        self.assertGreater(len(pieces),1)
        self.assertTrue(all(inside(original,p) for b in pieces for p in b.vertices))
        # The reveal removes only the front six units, with a solid back
        # through every slice, including their exact shared boundaries.
        for z in range(-320,-191):
            self.assertTrue(any(inside(b,(1064,1256,z)) for b in pieces))
        self.assertFalse(any(inside(b,(1002,1256,-286)) for b in pieces))
        self.assertTrue(any(inside(b,(1007,1256,-286)) for b in pieces))

    def test_angled_arch_jamb_does_not_get_nicked_at_its_end(self):
        lower=box(1000,1000,-600,1064,1064,-400,texture="aw_stone")
        upper=prism(((1000,-400),(1064,-400),(1096,-336),(1032,-336)),
                    1000,1064,1,"aw_stone")
        refined,edges=ease(lower,Solids([lower,upper]))
        self.assertTrue(inside(refined,(1000,1000,-400)))
        self.assertFalse(any(e["start"][:2]==e["end"][:2] for e in edges))

    def test_cornice_detail_has_the_same_envelope_and_a_simple_structural_core(self):
        beam=box(1000,1000,-320,1064,1512,-192,texture="aw_trim")
        arena=Map(shell="explicit");arena.structural(beam)
        expected,_=cornice(beam,Solids([beam]))
        profiles(arena,[beam],[beam])
        self.assertEqual(len(arena.details),1)
        self.assertEqual(len(arena.details[0].faces),6)
        self.assertEqual(arena.entities[0][0]["classname"],"func_detail_wall")
        actual=[*arena.details,*arena.entities[0][1]]
        for x in range(1000,1065,2):
            for z in range(-320,-191,2):
                point=(x,1256,z)
                self.assertEqual(any(inside(b,point) for b in expected),
                                 any(inside(b,point) for b in actual),point)


if __name__=="__main__":
    unittest.main()
