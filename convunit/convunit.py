import re
from decimal import Decimal, getcontext
import os


def multiply_number_str(s):
    """将字符串数字乘以100并格式化输出（去除多余零）"""
    try:
        d = Decimal(s)
        d = d * Decimal('100')
        s_val = format(d, 'f')
        if '.' in s_val:
            s_val = s_val.rstrip('0').rstrip('.')
        return s_val
    except:
        return s


def process_tree_content(content):
    """处理树文件内容，将特定位置的数字扩大100倍"""
    # 处理冒号后的第一个数字
    colon_pattern = r'(:\s*)([0-9.eE-]+)'

    def replace_colon(match):
        return match.group(1) + multiply_number_str(match.group(2))

    # 处理大括号内的两组数字
    braces_pattern = r'(\{\s*)([0-9.eE-]+)(\s*,\s*)([0-9.eE-]+)(\s*\})'

    def replace_braces(match):
        return (match.group(1) + multiply_number_str(match.group(2)) +
                match.group(3) + multiply_number_str(match.group(4)) +
                match.group(5))

    # 执行双重替换
    content = re.sub(colon_pattern, replace_colon, content)
    content = re.sub(braces_pattern, replace_braces, content)
    return content


def main():
    getcontext().prec = 10  # 设置Decimal运算精度

    while True:
        file_path = input("请输入树文件路径（格式如：\\A\\B\\C\\D\\E\\1.tre）：")

        # 处理路径格式（兼容Windows和Linux）
        normalized_path = os.path.normpath(file_path)
        if not os.path.isfile(normalized_path):
            print(f"错误：文件不存在 - {normalized_path}")
            continue

        # 读取原始文件
        try:
            with open(normalized_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"读取文件失败：{e}")
            continue

        # 处理内容
        processed_content = process_tree_content(content)

        # 生成输出路径
        base_name = os.path.basename(normalized_path)
        output_name = f"out-{base_name}"
        output_path = os.path.join(os.path.dirname(normalized_path), output_name)

        # 写入处理结果
        try:
            with open(output_path, 'w') as f:
                f.write(processed_content)
            print(f"处理完成！结果已保存至：{output_path}")
            break
        except Exception as e:
            print(f"写入文件失败：{e}")


if __name__ == "__main__":
    print("=== 树文件处理工具 ===")
    print("功能：将分支长度和HPD置信区间扩大100倍")
    main()