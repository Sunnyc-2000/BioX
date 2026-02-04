#design by zyc&DeepSeekR1-250528 202507
import os
import natsort
import sys
from datetime import datetime


def extract_sequences(folder_path, search_key, output_folder, log_file):
    output_path = os.path.join(output_folder, f"{search_key}.fasta")

    try:
        all_files = natsort.natsorted(os.listdir(folder_path))
    except Exception as e:
        log_file.write(f"错误：无法读取文件夹内容 - {str(e)}\n")
        print(f"错误：无法读取文件夹内容 - {str(e)}")
        return 0, 0

    total_files = len(all_files)
    matched_files = 0
    files_with_match = 0

    try:
        with open(output_path, 'w') as out_f:
            for filename in all_files:
                filepath = os.path.join(folder_path, filename)

                if not os.path.isfile(filepath):
                    continue

                file_matched = False

                try:
                    with open(filepath, 'r') as in_f:
                        content = in_f.read()
                        sequences = content.split('>')[1:]

                        for seq in sequences:
                            parts = seq.split('\n', 1)
                            if len(parts) < 2:
                                continue

                            header = ">" + parts[0].strip()
                            sequence = parts[1].replace('\n', '')

                            if search_key in header:
                                file_matched = True
                                matched_files += 1
                                clean_header = header.lstrip('>')
                                out_f.write(f">{filename}_{clean_header}\n{sequence}\n")

                except Exception as e:
                    error_msg = f"处理文件 {filename} 时出错: {str(e)}"
                    log_file.write(error_msg + "\n")
                    print(error_msg)

                if file_matched:
                    files_with_match += 1

        success_msg = f"操作完成: {search_key}"
        detail_msg = f"  共处理 {total_files} 个文件, {files_with_match} 个文件找到匹配序列, 共找到 {matched_files} 个匹配序列"
        result_msg = f"{success_msg}\n{detail_msg}\n结果保存至: {os.path.abspath(output_path)}"
        log_file.write(result_msg + "\n")
        print(result_msg)

        # 返回匹配状态：0表示无匹配，1表示有匹配
        return 1 if files_with_match > 0 else 0

    except Exception as e:
        error_msg = f"处理 {search_key} 时出错: {str(e)}"
        log_file.write(error_msg + "\n")
        print(error_msg)
        return -1  # 错误状态


def interactive_extractor():
    folder_path = input("请输入文件夹路径: ").strip()

    if not os.path.exists(folder_path):
        print(f"错误：路径不存在 '{folder_path}'")
        return

    output_folder = os.path.join(folder_path, "out")
    os.makedirs(output_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(output_folder, f"extraction_log_{timestamp}.txt")

    try:
        log_file = open(log_path, 'w', encoding='utf-8')
    except Exception as e:
        print(f"创建日志文件失败: {str(e)}")
        return

    print(f"\n运行日志已保存至: {log_path}")
    print("================================")
    print("提示：")
    print("- 可以一次性输入多个序列名称片段，以斜杠(/)分隔")
    print("  例如：trnI/cox1/16S/atp6")
    print("- 输入'stop'停止程序")
    print("================================")

    log_file.write(f"文件夹路径: {folder_path}\n")
    log_file.write(f"日志创建时间: {timestamp}\n\n")
    log_file.write("提示：可以一次性输入多个序列名称片段，以斜杠(/)分隔\n")
    log_file.write("输入'stop'停止程序\n\n")

    total_extractions = 0
    success_extractions = 0
    no_match_extractions = 0
    error_extractions = 0

    while True:
        input_str = input("\n请输入序列名称片段(多个请用/分隔): ").strip()

        # 检查停止命令
        if input_str.lower() == "stop":
            log_file.write(f"用户输入: {input_str}\n")
            log_file.write("\n用户选择停止程序\n")
            print("\n程序已停止。")
            break

        if not input_str:
            log_file.write("输入为空，跳过本次操作\n")
            print("输入为空，请重新输入")
            continue

        log_file.write(f"用户输入: {input_str}\n")
        log_file.write("---------------------------\n")

        # 分割输入的多个序列名称
        keys = [key.strip() for key in input_str.split('/') if key.strip()]
        total_extractions += len(keys)

        if not keys:
            log_file.write("未检测到有效序列名称片段\n")
            print("未检测到有效序列名称片段，请用/分隔")
            continue

        print(f"开始处理 {len(keys)} 个序列名称片段...")

        # 处理每个序列名称片段
        for i, key in enumerate(keys):
            log_file.write(f"处理序列片段 ({i + 1}/{len(keys)}): {key}\n")
            start_time = datetime.now()
            log_file.write(f"开始时间: {start_time.strftime('%H:%M:%S')}\n")

            # 执行提取
            result = extract_sequences(folder_path, key, output_folder, log_file)

            # 记录结果状态
            if result == 1:
                success_extractions += 1
            elif result == 0:
                no_match_extractions += 1
            else:
                error_extractions += 1

            # 记录时间
            end_time = datetime.now()
            duration = end_time - start_time
            log_file.write(f"结束时间: {end_time.strftime('%H:%M:%S')}\n")
            log_file.write(f"耗时: {duration.total_seconds():.2f}秒\n\n")

        print(f"完成 {len(keys)} 个序列名称片段的处理")

    # 关闭日志并显示结果
    log_file.write("\n处理结果汇总:\n")
    log_file.write(f"  总序列片段数: {total_extractions}\n")
    log_file.write(f"  成功提取数: {success_extractions}\n")
    log_file.write(f"  未找到匹配数: {no_match_extractions}\n")
    log_file.write(f"  错误数: {error_extractions}\n")

    log_file.close()

    print("\n所有操作已完成")
    print("================================")
    print(f"日志保存至: {log_path}")
    print("处理结果汇总:")
    print(f"  总序列片段数: {total_extractions}")
    print(f"  成功提取数: {success_extractions} (找到匹配序列)")
    print(f"  未找到匹配数: {no_match_extractions} (未找到匹配序列)")
    print(f"  错误数: {error_extractions} (处理时出错)")
    print("================================")

    # Windows系统保持窗口打开
    if sys.platform.startswith('win'):
        input("\n按Enter键退出...")


if __name__ == "__main__":
    print("序列提取工具 - 批量输入模式")
    print("================================")
    print("功能特点:")
    print("- 支持一次性输入多个序列名称片段 (用/分隔)")
    print("- 完整支持多行序列提取")
    print("- 自动创建输出文件夹 (out)")
    print("- 详细记录运行日志和处理结果")
    print("================================")

    interactive_extractor()