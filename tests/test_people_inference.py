import unittest

from wps_archive.people_inference import infer_people_names


MAPPING = [
    {"name": "韩宇潇", "priority": 10, "include_keywords": ["航空排放健康", "航空排放"]},
    {"name": "郭鹏", "priority": 10, "include_keywords": ["电厂排放健康", "电厂排放", "电厂", "火电", "电力排放", "燃煤电厂"]},
    {"name": "李孟如", "priority": 10, "include_keywords": ["造纸厂", "造纸行业"]},
    {
        "name": "麦泽霖",
        "priority": 10,
        "include_keywords": ["多物种反演", "伴随模型", "优化函数"],
        "exclude_keywords": ["AI辅助55版本", "55版本", "化学机制开发"],
    },
    {"name": "吴燕星", "priority": 10, "include_keywords": ["臭氧浓度", "臭氧机制", "NO2阈值", "季节机制"]},
    {
        "name": "何金玲",
        "priority": 20,
        "include_keywords": ["AI辅助55版本", "55版本", "化学机制开发", "CMAQ化学机制"],
    },
]


class PeopleInferenceTests(unittest.TestCase):
    def test_returns_empty_when_no_keywords_match(self):
        self.assertEqual(infer_people_names(topic="基金申请讨论", mapping=MAPPING), [])

    def test_matches_specific_person_from_topic(self):
        self.assertEqual(
            infer_people_names(topic="航空排放健康影响与空间异质性等科学问题", mapping=MAPPING),
            ["韩宇潇"],
        )

    def test_matches_guopeng_only_with_power_plant_qualifier(self):
        self.assertEqual(
            infer_people_names(topic="电厂排放健康影响与区域差异分析", mapping=MAPPING),
            ["郭鹏"],
        )

    def test_does_not_match_anyone_for_bare_generic_health_topic(self):
        self.assertEqual(
            infer_people_names(topic="健康影响", mapping=MAPPING),
            [],
        )

    def test_matches_model_topic(self):
        self.assertEqual(
            infer_people_names(topic="优化函数参数设置与结果量级问题", mapping=MAPPING),
            ["麦泽霖"],
        )

    def test_prefers_highest_scoring_rule(self):
        self.assertEqual(
            infer_people_names(topic="NO2阈值与季节机制转换点", mapping=MAPPING),
            ["吴燕星"],
        )

    def test_prefers_higher_priority_rule_for_chemistry_topic(self):
        self.assertEqual(
            infer_people_names(topic="AI辅助55版本伴随模型开发进展", mapping=MAPPING),
            ["何金玲"],
        )

    def test_exclude_keywords_can_block_otherwise_matching_rule(self):
        self.assertEqual(
            infer_people_names(topic="AI辅助55版本优化函数调试", mapping=MAPPING),
            ["何金玲"],
        )


if __name__ == "__main__":
    unittest.main()
