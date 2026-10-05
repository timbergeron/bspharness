from dataclasses import replace
import unittest

from bspharness import Bounds, Move, WalkRoute
from bspharness.qa import audit_log, audit_routes, camera_config
from bspharness.routes import routes_from_json


def player_dump(marker,origin,mode="MOVETYPE_WALK",health=100,ground=True):
    return (f"{marker}_BEGIN\nEDICT 1:\nclassname player\norigin '{origin}'\n"
            f"movetype {mode}\nhealth {health}\nflags FL_CLIENT"+
            (" | FL_ONGROUND" if ground else "")+f"\n{marker}_END\n")


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.route = WalkRoute("test",(0,0,24),(0,0,0),(Move(72),),Bounds((160,-16,20),(224,16,32)))
        self.log = (player_dump("BSPHARNESS_ROUTE_0_START","0 0 24")+
                    player_dump("BSPHARNESS_ROUTE_0_STEP_0","190 0 24")+
                    player_dump("BSPHARNESS_ROUTE_0_FINISH","200 0 24"))

    def test_runtime_collision_position_health_and_ground_are_required(self):
        self.assertTrue(audit_routes(self.log,[self.route])[0]["passed"])
        for changed in (self.log.replace("MOVETYPE_WALK","MOVETYPE_NOCLIP"),
                        self.log.replace("200 0 24","24 0 24"),self.log.replace("health 100","health 90"),
                        self.log.replace("FL_ONGROUND","FL_SWIM"),self.log.replace("0 0 24","64 0 24"),""):
            with self.subTest(log=changed):
                self.assertFalse(audit_routes(changed,[self.route])[0]["passed"])

    def test_intermediate_jump_checkpoint_is_checked(self):
        route = replace(self.route,actions=(Move(72,("forward","jump"),Bounds((100,-16,64),(220,16,128))),))
        self.assertFalse(audit_routes(self.log,[route])[0]["passed"])
        changed = self.log.replace("190 0 24","190 0 96")
        self.assertTrue(audit_routes(changed,[route])[0]["passed"])

    def test_scripts_disable_noclip_before_every_route_and_before_camera_god(self):
        camera = {"name":"view","origin":[0,0,128],"angles":[0,0,0]}
        config = camera_config([camera],[self.route])
        self.assertLess(config.index("noclip 0"),config.index("+forward"))
        self.assertLess(config.index("BSPHARNESS_ROUTE_0_FINISH_END"),config.index("god 1"))
        self.assertIn("-forward",config)
        self.assertIn("host_framerate 0.013888889",config)
        self.assertIn("host_timescale 0",config)
        self.assertIn("gamma 1",config)
        with self.assertRaisesRegex(ValueError,"unique"):
            camera_config([camera,camera])
        with self.assertRaises(ValueError):
            camera_config([{**camera,"origin":[0,0,float("nan")]}])

    def test_route_json_round_trip_and_injection_rejection(self):
        self.assertEqual(routes_from_json([self.route.metadata()]),(self.route,))
        for buttons in (("forward;quit",),("noclip",),("forward","forward")):
            with self.assertRaises(ValueError):
                Move(10,buttons)
        with self.assertRaises(ValueError):
            routes_from_json([self.route.metadata(),self.route.metadata()])

    def test_item_checks_use_height_and_distinct_runtime_edicts(self):
        log = player_dump("BSPHARNESS_AUDIT","0 0 24")
        log = log.replace("BSPHARNESS_AUDIT_END", "EDICT 2:\nclassname weapon_rocketlauncher\norigin '128 0 6'\nBSPHARNESS_AUDIT_END")
        log += "BSPHARNESS_QA_COMPLETE\n"
        item = {"classname":"weapon_rocketlauncher","origin":"128 0 24"}
        self.assertEqual(audit_log(log,[item]),[])
        self.assertTrue(audit_log(log,[{**item,"origin":"128 0 216"}]))
        self.assertTrue(audit_log(log,[item,item]))
        self.assertEqual(audit_log(log,[{**item,"origin":"128 0 216","spawnflags":"512"}]),[])
        self.assertTrue(audit_log(log.replace("health 100","health nan"),[]))
