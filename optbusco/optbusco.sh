#!/bin/bash

# 交互式获取路径
read -p "请输入目标路径: " target_path

# 检查路径是否存在
if [ ! -d "$target_path" ]; then
    echo "错误：路径 '$target_path' 不存在！"
    exit 1
fi

echo "目标路径: $target_path"
echo "当前目录: $(pwd)"

# 进入目标路径
cd "$target_path" || exit 1
echo "切换后目录: $(pwd)"

# 列出当前目录内容
echo "=== 当前目录内容 ==="
ls -la
echo "==================="

# 查找所有以"_busco_result_exercise"结尾的文件夹
echo "正在搜索匹配的文件夹..."
find . -maxdepth 1 -type d -name "*_busco_result_exercise" | while read -r folder; do
    echo "找到文件夹: $folder"
    
    # 检查文件夹是否存在
    if [ ! -d "$folder" ]; then
        echo "警告: 文件夹 $folder 不存在"
        continue
    fi
    
    # 提取变量部分
    folder_name=$(basename "$folder")
    variable=$(echo "$folder_name" | sed 's/_busco_result_exercise$//')
    
    echo "处理文件夹: $folder_name, 变量为: $variable"
    
    # 定义要处理的子目录
    subdirs=("single_copy_busco_sequences" "fragmented_busco_sequences")
    
    for subdir in "${subdirs[@]}"; do
        sequences_dir="$folder/run_endopterygota_odb10/busco_sequences/$subdir"
        echo "检查路径: $sequences_dir"
        
        # 检查子目录是否存在
        if [ -d "$sequences_dir" ]; then
            echo "  子目录存在: $subdir"
            
            # 列出子目录内容
            echo "  子目录内容:"
            ls -la "$sequences_dir" 2>/dev/null || echo "  无法列出目录内容"
            
            # 处理该目录下的所有.faa和.fna文件
            find "$sequences_dir" -maxdepth 1 -type f \( -name "*.faa" -o -name "*.fna" \) | while read -r file; do
                if [ -f "$file" ]; then
                    echo "    找到文件: $(basename "$file")"
                    echo "    文件路径: $file"
                    
                    # 显示文件前几行
                    echo "    文件前3行内容:"
                    head -3 "$file"
                    
                    # 创建临时文件
                    temp_file=$(mktemp)
                    
                    # 处理文件：将第一行替换为">变量"
                    echo "    执行sed命令..."
                    sed "1s/^>.*$/>$variable/" "$file" > "$temp_file"
                    
                    # 检查临时文件内容
                    echo "    修改后文件前3行:"
                    head -3 "$temp_file"
                    
                    # 用临时文件替换原文件
                    mv "$temp_file" "$file"
                    echo "    文件修改完成"
                else
                    echo "    警告: 文件 $file 不存在"
                fi
            done
        else
            echo "  警告: 子目录 $sequences_dir 不存在"
            # 检查路径的每一级是否存在
            echo "  路径检查:"
            if [ ! -d "$folder" ]; then
                echo "    $folder 不存在"
            elif [ ! -d "$folder/run_endopterygota_odb10" ]; then
                echo "    $folder/run_endopterygota_odb10 不存在"
            elif [ ! -d "$folder/run_endopterygota_odb10/busco_sequences" ]; then
                echo "    $folder/run_endopterygota_odb10/busco_sequences 不存在"
            else
                echo "    $folder/run_endopterygota_odb10/busco_sequences 存在，但缺少 $subdir 子目录"
            fi
        fi
    done
done

echo "处理完成！"
