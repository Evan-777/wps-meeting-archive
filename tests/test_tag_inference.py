import unittest

from wps_archive.tag_inference import infer_tags


class TagInferenceTests(unittest.TestCase):
    def test_defaults_to_plan_design(self):
        self.assertEqual(infer_tags("", ""), ["方案设计"])

    def test_prefers_data_analysis_for_threshold_topics(self):
        self.assertEqual(infer_tags(topic="NO2阈值与季节机制转换点"), ["数据分析", "研究方向及假设"])

    def test_marks_data_collection_and_analysis(self):
        self.assertEqual(infer_tags(topic="排放分析方法与造纸行业数据整理"), ["数据收集", "数据分析"])

    def test_marks_model_topics(self):
        self.assertEqual(infer_tags(topic="优化函数参数设置与结果量级问题"), ["数据分析", "模式模拟"])


if __name__ == "__main__":
    unittest.main()
