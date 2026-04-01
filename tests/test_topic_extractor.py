import unittest

from wps_archive.topic_extractor import extract_topic_from_recording_content


class TopicExtractorTests(unittest.TestCase):
    def test_prefers_more_specific_summary_over_generic_chapter_title(self):
        topic = extract_topic_from_recording_content(
            summary_text="## 关于优化函数参数设置与结果量级问题的讨论",
            chapters=[{"title": "优化函数参数设置问题讨论"}],
            transcript_text="",
        )
        self.assertEqual(topic, "优化函数参数设置与结果量级问题")

    def test_prefers_domain_terms_from_summary_content(self):
        topic = extract_topic_from_recording_content(
            summary_text="## 关于航空排放健康影响与论文修改的讨论会议\n\n重点涉及航空排放、健康影响和引言逻辑。",
            chapters=[{"title": "论文引言与科学问题讨论", "content": "引言部分需要突出航空排放的健康影响，并梳理科学问题和论文修改结构。"}],
            transcript_text="",
        )
        self.assertEqual(topic, "航空排放健康影响与科学问题")

    def test_extracts_professional_terms_from_generic_progress_title(self):
        topic = extract_topic_from_recording_content(
            summary_text="## 关于臭氧污染研究进展与文章撰写的讨论会议\n\n涉及NO2阈值、季节机制转换点和源汇。",
            chapters=[{"title": "文章进展与初步结果分享", "content": "目前臭氧季节变化、NO2阈值、季节机制转换点和源汇分析已经有了初步结果。"}],
            transcript_text="文章现在主要是臭氧季节变化和NO2阈值，还要继续分析季节机制转换点和源汇。",
        )
        self.assertEqual(topic, "NO2阈值与季节机制转换点")

    def test_falls_back_to_transcript_phrase(self):
        topic = extract_topic_from_recording_content(
            summary_text="",
            chapters=[],
            transcript_text="我们今天继续讨论臭氧机制分析，然后看参数设置。",
        )
        self.assertEqual(topic, "臭氧机制分析")

    def test_keeps_ai_version_signal_for_people_mapping(self):
        topic = extract_topic_from_recording_content(
            summary_text="## AI辅助55版本伴随模型开发进展",
            chapters=[],
            transcript_text="",
        )
        self.assertIn("AI辅助55版本", topic)


if __name__ == "__main__":
    unittest.main()
