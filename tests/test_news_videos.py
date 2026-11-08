import unittest

from news_videos import news_videos, youtube_id


class NewsVideoTests(unittest.TestCase):
    def test_youtube_id_from_common_urls(self):
        for u in ("dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3", "https://youtu.be/dQw4w9WgXcQ",
                  "https://www.youtube.com/shorts/dQw4w9WgXcQ", "https://www.youtube.com/embed/dQw4w9WgXcQ"):
            self.assertEqual(youtube_id(u), "dQw4w9WgXcQ", u)
        for bad in ("http://youtu.be/dQw4w9WgXcQ", "https://evil.com/watch?v=dQw4w9WgXcQ", "x", None):
            self.assertEqual(youtube_id(bad), "", bad)

    def test_youtube_and_clip_go_to_their_places(self):
        a = {"videos": [{"youtube": "https://youtu.be/dQw4w9WgXcQ", "start": 42, "placement": "top", "caption": "Discurso <ao vivo>", "credit": "TV Senado"},
                        {"clip": "clips/" + "a" * 64 + ".mp4", "placement": "analise", "caption": "Corte"},
                        {"clip": "../segredo.mp4"}, {"youtube": "https://evil.com/x"}]}
        v = news_videos(a, prefix="../../")
        self.assertIn('data-yt="dQw4w9WgXcQ" data-start="42"', v["top"])
        self.assertIn("Discurso &lt;ao vivo&gt; · Vídeo: TV Senado", v["top"])
        self.assertIn('src="../../clips/' + "a" * 64 + '.mp4"', v["analise"])
        self.assertEqual(v["fatos"] + v["contraponto"], "")
        self.assertIn("youtube-nocookie.com/embed/", v["style"])

    def test_translated_caption_and_no_videos(self):
        v = news_videos({"videos": [{"youtube": "dQw4w9WgXcQ", "caption": "pt"}]}, captions={"1": "English"}, play_label="Watch")
        self.assertIn("English", v["fatos"])
        self.assertEqual(news_videos({})["style"], "")


if __name__ == "__main__":
    unittest.main()
