# 运行迟分测试的简单脚本
import sys
import os

# 添加项目根目录到路径
project_root = "/Users/mini/Desktop/awesome-rag-cookbook"
sys.path.append(project_root)

# 运行测试
if __name__ == "__main__":
    print("开始运行迟分测试...")
    
    try:
        from tutorial.chunk_strategy.late_chunking.test_late_chunking import test_late_chunking, compare_with_traditional_chunking
    
        
        print("\n" + "="*60)
        print("运行比较测试")
        print("="*60)
        
        # 运行比较测试
        compare_with_traditional_chunking()
        
    except Exception as e:
        print(f"运行测试时出现错误: {e}")
        import traceback
        traceback.print_exc()
