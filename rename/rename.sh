#!/bin/bash

shopt -s extglob

# 日志记录函数
log() {
    local level=$1
    local message=$2
    local timestamp=$(TZ='Asia/Shanghai' date "+%Y-%m-%d %H:%M:%S")
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$log_file"
}

# 规范化路径函数
normalize_path() {
    local path=$(echo "$1" | sed 's/\\/\//g; s/\r//g; s/\/$//')
    if [[ $path == .* ]]; then
        echo "$(realpath -m "$path")"
    else
        echo "$path"
    fi
}

# 移除首尾空白字符
trim_whitespace() {
    local str="$1"
    str="${str#"${str%%[![:space:]]*}"}"  # 移除首部空白
    str="${str%"${str##*[![:space:]]}"}"  # 移除尾部空白
    echo -n "$str"
}

# 确保目录存在
ensure_directory() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1" && log "INFO" "创建目录: $1"
    fi
}

# 修复：避免在子shell中使用变量
rename_based_on_csv() {
    local csv_path norm_csv_path target_path norm_target_path log_dir norm_log_dir

    read -p "输入CSV文件路径: " csv_path
    read -p "输入目标文件夹路径: " target_path
    read -p "输入日志目录路径: " log_dir

    norm_csv_path=$(normalize_path "$csv_path")
    norm_target_path=$(normalize_path "$target_path")
    norm_log_dir=$(normalize_path "$log_dir")

    # 验证路径
    if [ ! -f "$norm_csv_path" ]; then
        log "ERROR" "CSV文件不存在: $norm_csv_path" && return 1
    fi
    if [ ! -d "$norm_target_path" ]; then
        log "ERROR" "目标目录不存在: $norm_target_path" && return 1
    fi

    ensure_directory "$norm_log_dir" || { log "ERROR" "无法创建日志目录: $norm_log_dir"; return 1; }

    log_file="${norm_log_dir}/rename_$(date +%Y%m%d_%H%M%S).log"
    echo "=== 重命名操作日志 ===" > "$log_file"
    log "INFO" "CSV路径: $norm_csv_path"
    log "INFO" "目标路径: $norm_target_path"

    declare -A rename_map
    local missing_in_fs=0 missing_in_csv=0 renamed=0 line_num=0 valid_lines=0

    {
        read
        while IFS=, read -r src_name target_name; do
            ((line_num++))
            src_name=$(trim_whitespace "${src_name//$'\r'/}")
            target_name=$(trim_whitespace "${target_name//$'\r'/}")
            [ -z "$src_name" ] && continue
            ((valid_lines++))
            rename_map["$src_name"]="$target_name"
        done
    } < <(sed 's/\r$//' "$norm_csv_path")

    log "INFO" "CSV解析完成 (总行数: $line_num, 有效条目: $valid_lines)"

    # 修复：使用数组存储结果避免子shell变量问题
    local processed_items=()
    log "INFO" "开始扫描: $norm_target_path"
    
    # 修复：使用while read循环代替find|pipe
    while IFS= read -r -d $'\0' item; do
        [ "$item" = "$norm_target_path" ] && continue
        local original_name=$(basename "$item")
        local item_type="文件"
        [ -d "$item" ] && item_type="文件夹"

        if [[ -n ${rename_map[$original_name]} ]]; then
            local new_name="${rename_map[$original_name]}"
            new_name=$(trim_whitespace "$new_name")

            if [ "$item_type" = "文件" ]; then
                local extension="${original_name##*.}"
                [[ "$original_name" != *.* ]] && extension=""
                [[ -n "$extension" ]] && new_name="${new_name}.${extension}"
            fi

            new_name=$(trim_whitespace "$new_name")
            local parent_dir=$(dirname "$item")
            local new_path="$parent_dir/$new_name"

            if mv -n "$item" "$new_path" 2>/dev/null; then
                log "SUCCESS" "$item_type [$original_name] -> [$new_name]"
                processed_items+=("$original_name")  # 记录成功项
                renamed=$((renamed + 1))
            else
                log "ERROR" "$item_type [$original_name] 重命名失败"
            fi
        else
            log "NOTICE" "$item_type [$original_name] 未找到匹配规则"
            missing_in_csv=$((missing_in_csv + 1))
        fi
    done < <(find "$norm_target_path" -maxdepth 1 -print0)

    # 从映射表中移除已处理项
    for orig_name in "${processed_items[@]}"; do
        unset "rename_map[$orig_name]"
    done

    # 检查剩余未使用的条目
    for key in "${!rename_map[@]}"; do
        log "WARNING" "CSV条目未使用: [$key] => [${rename_map[$key]}]"
        missing_in_fs=$((missing_in_fs + 1))
    done

    log "INFO" "====== 操作统计 ======"
    log "INFO" "成功重命名条目: $renamed"
    log "INFO" "未匹配CSV条目: $missing_in_csv"
    log "INFO" "未使用的CSV规则: $missing_in_fs"
}

# 主菜单
main_menu() {
    while true; do
        echo
        echo "请选择功能:"
        echo "1) CSV重命名"
        echo "q) 退出"
        read -p "选择: " choice
        case $choice in
            1) rename_based_on_csv ;;
            q|Q) exit 0 ;;
            *) echo "无效选择" ;;
        esac
    done
}

echo "==== 批量重命名工具 ===="
main_menu
