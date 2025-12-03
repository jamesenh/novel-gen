#!/usr/bin/env python3
"""
Mem0 健康检查脚本
检查 Mem0 连接状态和数据统计

使用方法:
    uv run python scripts/check_mem0_health.py
    uv run python scripts/check_mem0_health.py --project demo_001
"""
import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novelgen.config import ProjectConfig
from novelgen.runtime.mem0_manager import Mem0Manager


def check_health(project_name: str = "demo_001"):
    """检查 Mem0 健康状态"""
    print(f"\n{'='*60}")
    print(f"Mem0 健康检查: {project_name}")
    print(f"{'='*60}\n")
    
    # 加载项目配置
    project_dir = project_root / "projects" / project_name
    if not project_dir.exists():
        print(f"❌ 项目不存在: {project_dir}")
        return 1
    
    config = ProjectConfig(project_dir=str(project_dir))
    
    # 检查 Mem0 是否启用
    if not config.mem0_config or not config.mem0_config.enabled:
        print("⚠️ Mem0 未启用")
        print("\n要启用 Mem0，请在 .env 文件中添加:")
        print("  MEM0_ENABLED=true")
        print("  OPENAI_API_KEY=your_api_key")
        return 1
    
    # 初始化 Mem0 管理器
    manager = Mem0Manager(
        config=config.mem0_config,
        project_id=project_name,
        embedding_config=config.embedding_config
    )
    
    # 健康检查
    health = manager.health_check()
    
    print("状态信息:")
    print(f"  - 启用状态: {'✅ 已启用' if health['enabled'] else '❌ 未启用'}")
    print(f"  - 运行状态: {health['status']}")
    print(f"  - 消息: {health['message']}")
    
    if health['status'] == 'healthy':
        print(f"\n配置信息:")
        print(f"  - ChromaDB 路径: {health.get('chroma_path', 'N/A')}")
        print(f"  - Collection 名称: {health.get('collection', 'N/A')}")
        
        # 尝试获取数据统计
        try:
            print(f"\n数据统计:")
            
            # 用户偏好统计
            user_prefs = manager.get_all_user_preferences()
            print(f"  - 用户偏好数量: {len(user_prefs)}")
            
            if user_prefs:
                print(f"\n最近的用户偏好:")
                for i, pref in enumerate(user_prefs[:3], 1):
                    memory = pref.get('memory', 'N/A')
                    print(f"    {i}. {memory[:80]}...")
            
            print(f"\n✅ Mem0 运行正常！")
            return 0
            
        except Exception as e:
            print(f"\n⚠️ 数据统计获取失败: {e}")
            print("但 Mem0 连接正常，可以继续使用。")
            return 0
    else:
        print(f"\n❌ Mem0 存在问题")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Mem0 健康检查")
    parser.add_argument(
        "--project",
        type=str,
        default="demo_001",
        help="项目名称（默认: demo_001）"
    )
    
    args = parser.parse_args()
    
    try:
        exit_code = check_health(args.project)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ 检查过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

