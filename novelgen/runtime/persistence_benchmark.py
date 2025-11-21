"""
持久化性能基准脚本（Phase1）

对比开启/关闭持久化（数据库 + 向量存储）时，运行少量标准步骤的耗时。
本脚本不会在测试套件中自动运行，只用于手动观测和记录。

使用方式：
    python -m novelgen.runtime.persistence_benchmark

注意：脚本会调用 LLM，请确保已经正确配置 OPENAI_API_KEY 等环境变量。
"""

import os
import time
import tempfile
import shutil

from novelgen.runtime.orchestrator import NovelOrchestrator


def run_small_flow(
    project_name: str,
    base_dir: str,
    persistence_enabled: bool,
    vector_store_enabled: bool,
) -> float:
    """运行一个简化的 world -> theme -> characters 流程并返回耗时（秒）。"""

    # 保存旧环境变量
    old_persistence = os.getenv("NOVELGEN_PERSISTENCE_ENABLED")
    old_vector = os.getenv("NOVELGEN_VECTOR_STORE_ENABLED")

    try:
        os.environ["NOVELGEN_PERSISTENCE_ENABLED"] = "true" if persistence_enabled else "false"
        os.environ["NOVELGEN_VECTOR_STORE_ENABLED"] = "true" if vector_store_enabled else "false"

        start = time.perf_counter()
        orchestrator = NovelOrchestrator(project_name=project_name, base_dir=base_dir, verbose=False)

        # 注意：下面步骤会调用 LLM，需要正确配置 API Key
        orchestrator.step1_create_world("一个用于持久化性能测试的简化世界观", force=True)
        orchestrator.step2_create_theme_conflict("一个用于性能测试的主题与冲突", force=True)
        orchestrator.step3_create_characters(force=True)
        orchestrator.close()

        end = time.perf_counter()
        return end - start
    finally:
        # 恢复环境变量
        if old_persistence is None:
            os.environ.pop("NOVELGEN_PERSISTENCE_ENABLED", None)
        else:
            os.environ["NOVELGEN_PERSISTENCE_ENABLED"] = old_persistence

        if old_vector is None:
            os.environ.pop("NOVELGEN_VECTOR_STORE_ENABLED", None)
        else:
            os.environ["NOVELGEN_VECTOR_STORE_ENABLED"] = old_vector


def main() -> None:
    """运行持久化性能基准，并在控制台输出结果。"""

    temp_dir = tempfile.mkdtemp()
    try:
        base_dir = temp_dir
        print("=== 持久化性能基准（Phase1）===")
        print(f"临时项目根目录: {base_dir}")

        t_with_persistence = run_small_flow(
            project_name="bench_persistence_on",
            base_dir=base_dir,
            persistence_enabled=True,
            vector_store_enabled=True,
        )
        t_without_persistence = run_small_flow(
            project_name="bench_persistence_off",
            base_dir=base_dir,
            persistence_enabled=False,
            vector_store_enabled=False,
        )

        print()
        print(f"开启持久化: {t_with_persistence:.2f}s")
        print(f"关闭持久化: {t_without_persistence:.2f}s")
        if t_without_persistence > 0:
            overhead = t_with_persistence - t_without_persistence
            ratio = t_with_persistence / t_without_persistence
            print(f"绝对开销: {overhead:.2f}s, 比例: x{ratio:.2f}")

        print("\n提示：具体数值依赖于 LLM 延迟和本机性能，请在本地多次运行后再做结论，并视需要记录到文档或 issue 中。")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()

