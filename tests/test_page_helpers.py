from videopub.uploaders.douyin.pages.upload_page import DouyinUploadPage
from videopub.uploaders.wechat.pages.upload_page import WeChatUploadPage


def test_wechat_tag_text_starts_on_new_line():
    assert (
        WeChatUploadPage._build_tag_text(["血压计", "高血压"])
        == "\n#血压计 #高血压 "
    )


def test_douyin_tag_text_starts_on_new_line():
    assert (
        DouyinUploadPage._build_tag_text(["血压计", "高血压"])
        == "\n#血压计 #高血压 "
    )


def test_douyin_publish_success_ignores_sidebar_text():
    assert not DouyinUploadPage._body_indicates_publish_success("首页\n内容管理\n发布设置")
    assert DouyinUploadPage._body_indicates_publish_success("发布成功，点击查看作品")


def test_douyin_tag_text_is_single_line_of_hashtags():
    assert DouyinUploadPage._build_tag_text(["A", "B"]) == "\n#A #B "
