import os
import datetime
import shutil
import re
import time
import sys


def normalize_path(path):
    """处理路径中的斜杠和反斜杠问题"""
    return os.path.normpath(path.strip().replace('"', '').replace("'", ""))


def create_directory(dir_path):
    """创建目录（如果不存在）"""
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            return True, f"创建目录: {dir_path}"
        except Exception as e:
            return False, f"目录创建失败: {dir_path} - {str(e)}"
    return True, "目录已存在"


def process_fasta_file(input_path, output_path):
    """处理单个FASTA文件并修改标题行"""
    success = True
    error_msg = ""
    temp_path = output_path + ".tmp"
    fail_lines = []  # 记录匹配失败的行

    try:
        with open(input_path, 'r', encoding='utf-8') as infile, open(temp_path, 'w', encoding='utf-8') as outfile:
            for line in infile:
                if line.startswith('>'):
                    # 关键修复：使用更精准的正则表达式
                    match = re.search(r'\.fasta_([^;\n]+)', line)
                    if match:
                        new_header = '>' + match.group(1) + '\n'
                        outfile.write(new_header)
                    else:
                        # 记录匹配失败的行
                        fail_lines.append(line.strip())
                        outfile.write(line)
                else:
                    outfile.write(line)

        # 替换原文件
        shutil.move(temp_path, output_path)
        return True, "处理成功", fail_lines

    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"文件处理失败: {str(e)}", []


def main():
    print("\n===== FASTA文件处理器 =====")

    # 获取用户输入路径
    input_dir = normalize_path(input("请输入原始文件所在目录: "))
    output_dir = normalize_path(input("请输入处理后文件输出目录: "))
    log_path = normalize_path(input("请输入日志文件路径: "))

    # 重要安全措施：防止输入输出目录相同导致的覆盖问题
    if os.path.normpath(input_dir) == os.path.normpath(output_dir):
        print("错误：输入目录和输出目录不能相同，这会导致原始文件被覆盖！")
        sys.exit(1)

    # 创建输出目录
    success, msg = create_directory(output_dir)
    if not success:
        print(f"错误: {msg}")
        sys.exit(1)

    # 创建日志目录
    log_dir = os.path.dirname(log_path)
    if log_dir:
        success, msg = create_directory(log_dir)
        if not success:
            print(f"错误: {msg}")
            sys.exit(1)

    # 初始化日志
    start_time = time.time()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    processed_count = 0
    success_count = 0
    failure_count = 0
    special_cases = []
    unmatched_headers = []  # 记录未匹配的标题行

    # 记录初始信息
    log_lines = [
        f"FASTA文件处理日志",
        f"处理开始时间: {timestamp}",
        f"原始文件目录: {input_dir}",
        f"输出目录: {output_dir}",
        f"日志文件: {log_path}",
        "-" * 60
    ]

    # 处理文件
    print(f"\n开始处理 {input_dir} 中的文件...")
    file_count = len([f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))])
    processed_files = 0

    for filename in os.listdir(input_dir):
        if not os.path.isfile(os.path.join(input_dir, filename)):
            continue

        processed_files += 1
        processed_count += 1
        print(f"处理中: {filename} ({processed_files}/{file_count})")

        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

        success, msg, fail_lines = process_fasta_file(input_path, output_path)

        if success:
            success_count += 1
            log_entry = f"SUCCESS: {filename} - {msg}"
            if fail_lines:
                log_entry += f"\n  ✘ 未匹配的行: {fail_lines}"
                unmatched_headers.append(f"{filename}: {fail_lines}")
            log_lines.append(log_entry)
        else:
            failure_count += 1
            log_lines.append(f"ERROR: {filename} - {msg}")
            special_cases.append(filename)

    # 计算运行时间
    elapsed = time.time() - start_time
    time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    completion_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 添加统计信息
    log_lines.extend([
        "-" * 60,
        f"处理完成时间: {completion_time}",
        f"总处理时间: {time_str}",
        f"扫描文件数: {processed_count}",
        f"成功处理: {success_count}",
        f"处理失败: {failure_count}",
        f"未匹配标题行数: {len(unmatched_headers)}"
    ])

    # 添加特殊情况记录
    if special_cases or unmatched_headers:
        log_lines.append("\n特殊情况报告:")

        if special_cases:
            log_lines.append("处理失败的文件列表:")
            log_lines.extend([f"  - {f}" for f in special_cases])
            log_lines.append(f"总计 {len(special_cases)} 个文件需要手动检查")

        if unmatched_headers:
            log_lines.append("\n未匹配标题行的文件:")
            log_lines.extend([f"  - {f}" for f in unmatched_headers])
            log_lines.append(f"总计 {len(unmatched_headers)} 个文件有未匹配的标题行")

        log_lines.append("\n建议: 检查这些文件的标题行格式是否符合预期的 '*.fasta_xxxx;' 格式")
    else:
        log_lines.append("\n所有文件处理成功，没有发现特殊情况")

    # 写入日志文件
    try:
        with open(log_path, 'w', encoding='utf-8') as log_file:
            log_file.write("\n".join(log_lines))
        print(f"\n处理完成! 详细日志已保存至: {log_path}")
        print(f"处理统计: 文件总数={processed_count}, 成功={success_count}, 失败={failure_count}")
        if unmatched_headers:
            print(f"警告: 有 {len(unmatched_headers)} 个文件存在标题行匹配问题，请检查日志")
    except Exception as e:
        print(f"日志写入失败: {str(e)}")
        # 在控制台输出日志作为备份
        print("\n重要: 无法写入日志文件，以下为处理摘要:")
        print("\n".join(log_lines[-15:]))


if __name__ == "__main__":
    main()