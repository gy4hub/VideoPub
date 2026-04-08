"""CLI 冒烟测试"""

from click.testing import CliRunner

from videopub.cli import cli

runner = CliRunner()


class TestCLIHelp:
    def test_main_help(self):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "多平台视频发布" in result.output
        assert "upload" in result.output
        assert "watch" in result.output
        assert "login" in result.output
        assert "status" in result.output

    def test_upload_help(self):
        result = runner.invoke(cli, ["upload", "--help"])
        assert result.exit_code == 0
        assert "FOLDER" in result.output
        assert "--platform" in result.output

    def test_watch_help(self):
        result = runner.invoke(cli, ["watch", "--help"])
        assert result.exit_code == 0
        assert "FOLDER" in result.output

    def test_login_help(self):
        result = runner.invoke(cli, ["login", "--help"])
        assert result.exit_code == 0
        assert "PLATFORM" in result.output

    def test_status_help(self):
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0


class TestCLIVersion:
    def test_version(self):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.1.0" in result.output
