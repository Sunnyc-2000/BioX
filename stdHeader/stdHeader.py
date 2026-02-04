import os
import glob
import re


def main():
    # 用户选择运行模式
    print("请选择运行模式:")
    print("1. 删除序列换行并统计字符数")
    print("2. 根据文件名修改序列头")
    print("3. 同时执行以上两种功能")
    mode = input("> 请输入数字 (1/2/3): ")

    if mode not in ('1', '2', '3'):
        print("错误: 无效模式选择，请输入1、2或3")
        return

    # 获取输入路径
    path = input("请输入文件路径 (如 /a/b/c):\n> ")

    # 创建处理结果目录
    output_dir = os.path.join(path, "processed_results")
    os.makedirs(output_dir, exist_ok=True)

    # 日志文件路径
    log_file = os.path.join(output_dir, "processing_log.txt")

    # 获取所有FASTA文件
    files = glob.glob(os.path.join(path, "*.fas")) + glob.glob(os.path.join(path, "*.fasta"))

    if not files:
        print(f"错误: 在路径 {path} 下未找到.fas或.fasta文件")
        return

    # 处理所有文件
    with open(log_file, 'w') as log:
        log_content = []

        if mode == '1':
            log_content.append("== 模式1处理日志 ==")
            for file in files:
                result = process_mode1(file, output_dir)
                if result:
                    log_content.append(result)

        elif mode == '2':
            log_content.append("== 模式2处理日志 ==")
            for file in files:
                result = process_mode2(file, output_dir)
                if result:
                    log_content.extend(result)

        elif mode == '3':
            log_content.append("== 模式3处理日志 ==")
            for file in files:
                result = process_mode3(file, output_dir)
                if result:
                    log_content.extend(result)

        log.write("\n".join(log_content))

    print(f"\n处理完成! 结果保存在: {output_dir}")
    print(f"日志文件: {log_file}")


def get_base_name(file_path):
    """获取不含扩展名的文件名"""
    base = os.path.basename(file_path)
    return os.path.splitext(base)[0]


def process_mode1(input_file, output_dir):
    """模式1：删除序列换行并统计字符数"""
    base_name = get_base_name(input_file)
    output_file = os.path.join(output_dir, os.path.basename(input_file))

    try:
        with open(input_file, 'r') as f:
            content = f.read()

        # 分割为序列块
        blocks = []
        current_header = None
        current_sequence = []

        for line in content.splitlines():
            if line.startswith('>'):
                # 保存前一个块
                if current_header is not None:
                    blocks.append((current_header, ''.join(current_sequence)))
                current_header = line
                current_sequence = []
            else:
                current_sequence.append(line.strip())

        # 保存最后一个块
        if current_header is not None:
            blocks.append((current_header, ''.join(current_sequence)))

        # 生成新内容并写入文件
        total_chars = 0
        output_lines = []

        for header, sequence in blocks:
            output_lines.append(header)
            output_lines.append(sequence)
            total_chars += len(sequence)

        with open(output_file, 'w') as f_out:
            f_out.write("\n".join(output_lines))

        return f"- {os.path.basename(input_file)}: 序列总字符数 = {total_chars}"

    except Exception as e:
        return f"错误处理文件 {input_file}: {str(e)}"


def process_mode2(input_file, output_dir):
    """模式2：根据文件名修改序列头"""
    base_name = get_base_name(input_file)
    output_file = os.path.join(output_dir, os.path.basename(input_file))

    try:
        with open(input_file, 'r') as f:
            content = f.read()

        # 分割为序列块
        blocks = []
        current_header = None
        current_sequence = []

        for line in content.splitlines():
            if line.startswith('>'):
                # 保存前一个块
                if current_header is not None:
                    blocks.append((current_header, '\n'.join(current_sequence)))
                current_header = line
                current_sequence = []
            else:
                current_sequence.append(line)

        # 保存最后一个块
        if current_header is not None:
            blocks.append((current_header, '\n'.join(current_sequence)))

        # 修改序列头
        output_lines = []
        log_entries = []
        sequence_count = len(blocks)

        for i, (header, sequence) in enumerate(blocks):
            original_header = header

            # 根据序列数量决定格式
            if sequence_count == 1:
                new_header = f">{base_name}"
            else:
                new_header = f">{base_name}_{i + 1}"

            log_entries.append(f"  - {os.path.basename(input_file)}: '{original_header}' -> '{new_header}'")
            output_lines.append(new_header)
            output_lines.append(sequence)

        # 写入输出文件
        with open(output_file, 'w') as f_out:
            f_out.write("\n".join(output_lines))

        return [
            f"- {os.path.basename(input_file)} 修改记录:",
            *log_entries
        ]

    except Exception as e:
        return [f"错误处理文件 {input_file}: {str(e)}"]


def process_mode3(input_file, output_dir):
    """模式3：同时执行模式1和2的功能"""
    base_name = get_base_name(input_file)
    output_file = os.path.join(output_dir, os.path.basename(input_file))

    try:
        with open(input_file, 'r') as f:
            content = f.read()

        # 分割为序列块
        blocks = []
        current_header = None
        current_sequence_lines = []

        for line in content.splitlines():
            if line.startswith('>'):
                # 保存前一个块
                if current_header is not None:
                    blocks.append((current_header, current_sequence_lines))
                current_header = line
                current_sequence_lines = []
            else:
                current_sequence_lines.append(line)

        # 保存最后一个块
        if current_header is not None:
            blocks.append((current_header, current_sequence_lines))

        # 处理序列块（修改头+合并序列行）
        output_lines = []
        log_entries = []
        sequence_count = len(blocks)
        total_chars = 0

        for i, (header, sequence_lines) in enumerate(blocks):
            original_header = header

            # 修改序列头
            if sequence_count == 1:
                new_header = f">{base_name}"
            else:
                new_header = f">{base_name}_{i + 1}"

            # 合并序列行
            sequence = ''.join(line.strip() for line in sequence_lines)
            total_chars += len(sequence)

            log_entries.append(f"  - 序列头: '{original_header}' -> '{new_header}'")
            output_lines.append(new_header)
            output_lines.append(sequence)

        # 写入输出文件
        with open(output_file, 'w') as f_out:
            f_out.write("\n".join(output_lines))

        return [
            f"- {os.path.basename(input_file)} 处理结果:",
            *log_entries,
            f"  序列总字符数 = {total_chars}"
        ]

    except Exception as e:
        return [f"错误处理文件 {input_file}: {str(e)}"]


if __name__ == "__main__":
    main()