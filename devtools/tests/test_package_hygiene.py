"""发布物卫生用例

- 拷贝名单只有本体自己的两棵树，隔壁仓供件不随包走
- 版本控制条目混进源树时被跳过，真落进发布目录则出包前当场停下
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "packaging"))

import build  # noqa: E402


class TestCopyList(unittest.TestCase):
    """拷贝名单"""

    def test_mount_root_is_not_shipped(self) -> None:
        """名单里只有本体自己的两棵树"""
        self.assertEqual(build._COPY_DIRS, ("src", "assets"))


class TestCopyIgnore(unittest.TestCase):
    """名单跳过版本控制条目"""

    def _stage(self) -> tuple[Path, Path]:
        """造一棵带版本控制条目与整树的源树，回源目录与发布目录"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        source = root / "out" / "src" / "bundled"
        source.mkdir(parents=True)
        (source / "entry.py").write_text("MARK = 1\n", encoding="utf-8")
        (source / ".git").write_text("gitdir: /somewhere\n", encoding="utf-8")
        nested = source / "features" / ".git"
        nested.mkdir(parents=True)
        (nested / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        return root, root / "stage"

    def test_git_entries_are_skipped(self) -> None:
        """版本控制条目不进发布目录，正文照常带过去"""
        root, stage = self._stage()
        shutil.copytree(
            root / "out",
            stage,
            ignore=shutil.ignore_patterns(*build._COPY_IGNORE),
        )
        self.assertTrue((stage / "src" / "bundled" / "entry.py").is_file())
        self.assertEqual([str(p) for p in stage.rglob(".git")], [])

    def test_guard_passes_clean_stage(self) -> None:
        """干净目录不该有声"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        stage = Path(holder.name)
        (stage / "src").mkdir()
        build._refuse_leftovers(stage)


class TestRefuseLeftovers(unittest.TestCase):
    """漏网即停"""

    def test_named_offender_is_reported(self) -> None:
        """报出条目相对发布目录的位置，不许只说有东西"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        stage = Path(holder.name)
        guilty = stage / "src" / "bundled"
        guilty.mkdir(parents=True)
        (guilty / ".git").write_text("gitdir: /somewhere\n", encoding="utf-8")
        with self.assertRaises(RuntimeError) as ctx:
            build._refuse_leftovers(stage)
        self.assertIn("src/bundled/.git", str(ctx.exception).replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
