import os
import re
import time
import datetime
import logging
import platform


def normalize_path(path_str):
    """处理不同操作系统的路径分隔符问题，并规范化路径"""
    # 处理特殊符号和空格
    clean_path = path_str.replace('•', '').strip()
    # 替换所有类型的分隔符为当前系统分隔符
    normalized = os.path.normpath(clean_path.replace('/', os.sep).replace('\\', os.sep))
    return normalized


def create_directory(path):
    """创建目录（如果不存在）"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"无法创建目录 {path}: {e}")
        return False


def get_new_filename(first_line, rename_mode, original_name):
    """从文件第一行提取新文件名"""
    try:
        if not first_line.startswith('>'):
            return None, "第一行不以'>'开头"

        # 提取第一个分号前的内容
        match = re.match(r'^>([^;]+)', first_line)
        if not match:
            return None, "无法解析第一行内容"

        base_name = match.group(1).strip()
        if not base_name:
            return None, "文件名为空"

        # 保留原始文件扩展名
        ext = os.path.splitext(original_name)[1]

        # 修改：如果rename_mode为空，则不添加下划线
        if rename_mode.strip():  # 如果rename_mode不为空（去除空格后）
            new_name = f"{base_name}_{rename_mode}{ext}"
        else:
            new_name = f"{base_name}{ext}"

        return new_name, None
    except Exception as e:
        return None, f"处理文件名时出错: {e}"


def main():
    # 收集用户输入
    source_dir = input("提示：运行本脚本之前请提前将aa和nt文件放到不同的文件夹中。请输入被处理文件夹路径: ")
    log_dir = input("请输入日志输出路径: ")
    rename_mode = input("请输入文件名后缀: ")

    # 规范化路径
    source_path = normalize_path(source_dir)
    log_path = normalize_path(log_dir)

    # 检查源目录是否存在
    if not os.path.exists(source_path):
        print(f"错误: 源目录不存在 {source_path}")
        return

    # 创建日志目录（如果需要）
    if not create_directory(log_path):
        return

    # 设置日志文件名（含时间戳）
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_path, f"rename_log_{timestamp}.txt")

    # 配置日志
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 记录初始信息
    start_time = time.time()
    start_beijing = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"脚本启动时间 (北京时间): {start_beijing}")
    logging.info(f"源目录: {source_path}")
    logging.info(f"日志目录: {log_path}")
    logging.info(f"重命名模式: '{rename_mode}'")  # 添加引号以便看清空模式

    # 处理文件
    file_count = 0
    success_count = 0
    fail_count = 0
    skipped_count = 0

    for filename in os.listdir(source_path):
        file_path = os.path.join(source_path, filename)

        # 跳过子目录
        if os.path.isdir(file_path):
            continue

        file_count += 1

        try:
            # 打开并读取第一行
            with open(file_path, 'r') as file:
                first_line = file.readline().strip()

            # 生成新文件名
            new_name, error_msg = get_new_filename(first_line, rename_mode, filename)

            if not new_name:
                logging.warning(f"跳过文件 {filename}: {error_msg}")
                skipped_count += 1
                continue

            # 构建新路径
            new_path = os.path.join(source_path, new_name)

            # 避免覆盖现有文件
            if os.path.exists(new_path):
                logging.warning(f"重命名冲突: {filename} -> {new_name} 已存在")
                skipped_count += 1
                continue

            # 执行重命名
            os.rename(file_path, new_path)
            success_count += 1
            logging.info(f"重命名成功: {filename} -> {new_name}")

        except Exception as e:
            fail_count += 1
            logging.error(f"处理文件 {filename} 时出错: {str(e)}", exc_info=True)

    # 计算运行时间
    end_time = time.time()
    run_duration = end_time - start_time
    end_beijing = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')

    # 最终日志统计
    logging.info("\n===== 操作统计 =====")
    logging.info(f"处理文件总数: {file_count}")
    logging.info(f"成功重命名文件: {success_count}")
    logging.info(f"重命名失败文件: {fail_count}")
    logging.info(f"跳过文件: {skipped_count}")
    logging.info(f"运行时间: {run_duration:.2f} 秒")
    logging.info(f"脚本结束时间 (北京时间): {end_beijing}")

    print("\n操作完成! 日志已保存至:")
    print(log_filename)
    print(f"\n统计信息:")
    print(f"总文件: {file_count} | 成功: {success_count} | 失败: {fail_count} | 跳过: {skipped_count}")
    print(f"耗时: {run_duration:.2f} 秒")


if __name__ == "__main__":
    main()