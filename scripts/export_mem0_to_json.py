#!/usr/bin/env python3
"""
Mem0 数据导出脚本
导出 Mem0 记忆到 JSON 文件

使用方法:
    uv run python scripts/export_mem0_to_json.py --project demo_001
    uv run python scripts/export_mem0_to_json.py --project demo_001 --output backup.json
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novelgen.config import ProjectConfig
from novelgen.runtime.mem0_manager import Mem0Manager


def export_mem0_data(project_name: str, output_file: str = None):
    """导出 Mem0 数据到 JSON"""
    print(f"\n{'='*60}")
    print(f"Mem0 数据导出: {project_name}")
    print(f"{'='*60}\n")
    
    # 加载项目配置
    project_dir = project_root / "projects" / project_name
    if not project_dir.exists():
        print(f"❌ 项目不存在: {project_dir}")
        return 1
    
    config = ProjectConfig(project_dir=str(project_dir))
    
    # 检查 Mem0 是否启用
    if not config.mem0_config or not config.mem0_config.enabled:
        print("⚠️ Mem0 未启用，无法导出数据")
        return 1
    
    # 初始化 Mem0 管理器
    manager = Mem0Manager(
        config=config.mem0_config,
        project_id=project_name,
        embedding_config=config.embedding_config
    )
    
    # 健康检查
    health = manager.health_check()
    if health['status'] != 'healthy':
        print(f"❌ Mem0 状态异常: {health['message']}")
        return 1
    
    print("正在导出数据...\n")
    
    try:
        # 导出用户偏好
        user_prefs = manager.get_all_user_preferences()
        print(f"✅ 用户偏好: {len(user_prefs)} 条")
        
        # 准备导出数据
        export_data = {
            "project_id": project_name,
            "export_time": datetime.now().isoformat(),
            "mem0_config": {
                "chroma_path": config.mem0_config.chroma_path,
                "collection_name": config.mem0_config.collection_name,
            },
            "data": {
                "user_preferences": user_prefs,
            }
        }
        
        # 确定输出文件名
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"mem0_export_{project_name}_{timestamp}.json"
        
        # 写入 JSON 文件
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ 数据已导出到: {output_path.absolute()}")
        print(f"  - 文件大小: {output_path.stat().st_size / 1024:.2f} KB")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    parser = argparse.ArgumentParser(description="导出 Mem0 数据到 JSON")
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="项目名称"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件名（默认: mem0_export_<project>_<timestamp>.json）"
    )
    
    args = parser.parse_args()
    
    try:
        exit_code = export_mem0_data(args.project, args.output)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ 导出过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

