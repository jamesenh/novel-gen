#!/usr/bin/env python3
"""
Mem0 记忆清理脚本
清理指定项目的 Mem0 记忆数据（用于测试）

警告: 此操作不可逆！建议先使用 export_mem0_to_json.py 导出备份。

使用方法:
    uv run python scripts/clear_mem0_memory.py --project demo_001
    uv run python scripts/clear_mem0_memory.py --project demo_001 --confirm
"""
import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novelgen.config import ProjectConfig
from novelgen.runtime.mem0_manager import Mem0Manager


def clear_mem0_data(project_name: str, confirm: bool = False):
    """清理 Mem0 数据"""
    print(f"\n{'='*60}")
    print(f"Mem0 记忆清理: {project_name}")
    print(f"{'='*60}\n")
    
    # 加载项目配置
    project_dir = project_root / "projects" / project_name
    if not project_dir.exists():
        print(f"❌ 项目不存在: {project_dir}")
        return 1
    
    config = ProjectConfig(project_dir=str(project_dir))
    
    # 检查 Mem0 是否启用
    if not config.mem0_config or not config.mem0_config.enabled:
        print("⚠️ Mem0 未启用，无需清理")
        return 0
    
    # 初始化 Mem0 管理器
    manager = Mem0Manager(
        config=config.mem0_config,
        project_id=project_name,
        embedding_config=config.embedding_config
    )
    
    # 健康检查
    health = manager.health_check()
    if health['status'] != 'healthy':
        print(f"⚠️ Mem0 状态异常: {health['message']}")
        print("可能已经清空，或连接失败。")
        return 1
    
    # 显示当前数据统计
    try:
        user_prefs = manager.get_all_user_preferences()
        print(f"当前数据统计:")
        print(f"  - 用户偏好: {len(user_prefs)} 条")
        print()
    except Exception as e:
        print(f"⚠️ 无法获取数据统计: {e}\n")
    
    # 确认操作
    if not confirm:
        print("⚠️ 警告：此操作将清空项目的所有 Mem0 记忆数据！")
        print(f"   ChromaDB 路径: {config.mem0_config.chroma_path}")
        print(f"   Collection: {config.mem0_config.collection_name}")
        print()
        print("建议先导出备份:")
        print(f"  uv run python scripts/export_mem0_to_json.py --project {project_name}")
        print()
        response = input("确认清空？(yes/no): ")
        if response.lower() != 'yes':
            print("❌ 操作已取消")
            return 0
    
    # 执行清空操作
    print("\n正在清空 Mem0 记忆...")
    try:
        success = manager.clear_project_memory()
        if success:
            print("✅ Mem0 记忆已清空")
            return 0
        else:
            print("❌ 清空操作失败")
            return 1
    except Exception as e:
        print(f"❌ 清空过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    parser = argparse.ArgumentParser(description="清理 Mem0 记忆数据")
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="项目名称"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="跳过确认提示，直接执行清理"
    )
    
    args = parser.parse_args()
    
    try:
        exit_code = clear_mem0_data(args.project, args.confirm)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ 清理过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

