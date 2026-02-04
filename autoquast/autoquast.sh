#!/bin/bash

# 交互式脚本：SPAdes输出处理与QUAST分析
# 支持三种操作模式：
#   1. 仅复制和重命名SPAdes输出文件
#   2. 复制重命名后运行QUAST质量评估
#   3. 对固定目录结构直接运行QUAST分析（保持原始文件名）

# 获取脚本启动时间
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SCRIPT_NAME=$(basename "$0" .sh)

# 日志文件位置将根据模式动态设置
LOG_FILE=""

# 定义常用颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 重置颜色

# 标题显示
echo -e "${BLUE}"
echo "=============================================="
echo " SPAdes Output Processing & QUAST Analysis Tool "
echo "     支持固定目录结构分析 (模式3)            "
echo "=============================================="
echo -e "${NC}"

# 日志函数
log() {
    local msg="$1"
    if [ -n "$LOG_FILE" ]; then
        echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] $msg${NC}" | tee -a "$LOG_FILE"
    else
        echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] $msg${NC}"
    fi
}

# 用户输入函数
user_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local required="$4"
    
    while true; do
        if [ -n "$default" ]; then
            echo -en "${YELLOW}$prompt [默认: ${GREEN}$default${YELLOW}]: ${NC}"
        else
            echo -en "${YELLOW}$prompt: ${NC}"
        fi
        
        read input
        if [ -z "$input" ]; then
            input="$default"
        fi
        
        if [ "$required" = "required" ] && [ -z "$input" ]; then
            echo -e "${RED}此项为必填项，请重新输入${NC}"
        else
            break
        fi
    done
    
    eval $var_name="'$input'"
    log "用户输入: $prompt = $input"
}

# 模式选择
while true; do
    echo -e "${YELLOW}请选择操作模式："
    echo -e "1: 仅复制重命名SPAdes输出文件"
    echo -e "2: 复制重命名+运行QUAST分析"
    echo -e "3: 对固定目录结构运行QUAST (保持原文件名)${NC}"
    echo -en "${YELLOW}请输入选择(1,2或3): ${NC}"
    
    read MODE
    case $MODE in
        1|2|3)
            log "选择模式: $MODE"
            break
            ;;
        *)
            echo -e "${RED}无效选择，请重新输入${NC}"
            ;;
    esac
done

# 路径输入部分
echo -e "\n${BLUE}================ 路径配置 ================${NC}"

if [ "$MODE" = "1" ] || [ "$MODE" = "2" ]; then
    user_input "输入SPAdes结果根路径 (如: /1/2/3/4)" "" "SOURCE_PATH" "required"
    user_input "输入目标路径 (复制重命名后的文件存放路径)" "" "COPY_TARGET" "required"
fi

if [ "$MODE" = "2" ]; then
    user_input "输入QUAST输出路径" "" "QUAST_OUTPUT" "required"
fi

if [ "$MODE" = "3" ]; then
    user_input "输入物种根目录 (包含各个物种目录的路径)" "" "SPECIES_ROOT" "required"
    user_input "输入QUAST输出路径" "" "QUAST_OUTPUT" "required"
    # 设置日志文件为QUAST输出目录
    LOG_FILE="${QUAST_OUTPUT}/processing_${TIMESTAMP}.log"
    touch "$LOG_FILE"
fi

# 如果未设置日志文件，设置默认位置
if [ -z "$LOG_FILE" ]; then
    LOG_FILE="processing_${TIMESTAMP}.log"
    touch "$LOG_FILE"
fi

log "日志文件设置为: $LOG_FILE"

# QUAST可执行路径
QUAST_CMD="/home/insect303/tools/quast-5.3.0/quast.py"

# 显示配置摘要
echo -e "\n${BLUE}============== 配置摘要 ==============${NC}"
echo -e "${YELLOW}操作模式:     ${GREEN}$MODE${NC}"
if [ "$MODE" = "1" ] || [ "$MODE" = "2" ]; then
    echo -e "${YELLOW}源路径:        ${GREEN}$SOURCE_PATH${NC}"
    echo -e "${YELLOW}目标路径:      ${GREEN}$COPY_TARGET${NC}"
fi
if [ "$MODE" = "2" ] || [ "$MODE" = "3" ]; then
    echo -e "${YELLOW}QUAST输出路径: ${GREEN}$QUAST_OUTPUT${NC}"
fi
if [ "$MODE" = "3" ]; then
    echo -e "${YELLOW}物种根目录:    ${GREEN}$SPECIES_ROOT${NC}"
fi
echo -e "${YELLOW}日志文件:      ${GREEN}$LOG_FILE${NC}"
echo -e "${BLUE}========================================${NC}"

# 配置确认
while true; do
    echo -en "${YELLOW}是否开始执行?(y/n): ${NC}"
    read confirm
    case $confirm in
        [Yy]* )
            log "用户确认执行"
            break
            ;;
        [Nn]* )
            log "用户取消执行"
            exit 0
            ;;
        * )
            echo -e "${RED}请输入 y 或 n${NC}"
            ;;
    esac
done

# ========================================================================
# 处理函数：复制和重命名文件
# ========================================================================
process_spades() {
    local total_dirs=0
    local success_dirs=0
    local missing_contigs=0
    local missing_scaffolds=0
    local other_errors=0

    log "开始处理SPAdes输出文件..."
    log "源路径: $SOURCE_PATH"
    log "目标路径: $COPY_TARGET"

    # 创建目标目录结构
    mkdir -p "$COPY_TARGET"

    # 处理每个样品目录
    for dir in "$SOURCE_PATH"/*; do
        if [ ! -d "$dir" ]; then
            continue
        fi
        
        local dir_name=$(basename "$dir")
        local spades_path="$dir/spades"
        ((total_dirs++))
        
        log "处理样品: $dir_name"
        
        # 检查spades目录
        if [ ! -d "$spades_path" ]; then
            log "  ${RED}错误${NC}: 缺失spades目录"
            ((other_errors++))
            continue
        fi

        # 检查目标文件
        local contigs_src="$spades_path/contigs.fasta"
        local scaffolds_src="$spades_path/scaffolds.fasta"
        local has_contigs=0
        local has_scaffolds=0
        
        if [ -f "$contigs_src" ]; then
            has_contigs=1
        else
            log "  ${YELLOW}警告${NC}: contigs.fasta 未找到"
            ((missing_contigs++))
        fi
        
        if [ -f "$scaffolds_src" ]; then
            has_scaffolds=1
        else
            log "  ${YELLow}警告${NC}: scaffolds.fasta 未找到"
            ((missing_scaffolds++))
        fi

        # 创建目标目录
        local target_dir="$COPY_TARGET/$dir_name"
        mkdir -p "$target_dir"
        
        if [ ! -d "$target_dir" ]; then
            log "  ${RED}错误${NC}: 无法创建目标目录"
            ((other_errors++))
            continue
        fi

        # 复制并重命名文件
        if [ $has_contigs -eq 1 ]; then
            cp "$contigs_src" "$target_dir/${dir_name}_contigs.fasta"
            log "  复制 contigs.fasta → ${GREEN}${dir_name}_contigs.fasta${NC}"
        fi
        
        if [ $has_scaffolds -eq 1 ]; then
            cp "$scaffolds_src" "$target_dir/${dir_name}_scaffolds.fasta"
            log "  复制 scaffolds.fasta → ${GREEN}${dir_name}_scaffolds.fasta${NC}"
        fi

        ((success_dirs++))
    done

    # 结果统计
    echo -e "\n${BLUE}========== 复制重命名结果 ==========${NC}" | tee -a "$LOG_FILE"
    echo -e "处理样品总数:   $total_dirs" | tee -a "$LOG_FILE"
    echo -e "成功处理样品数: $success_dirs" | tee -a "$LOG_FILE"
    echo -e "缺失contigs样品: $missing_contigs" | tee -a "$LOG_FILE"
    echo -e "缺失scaffolds样品: $missing_scaffolds" | tee -a "$LOG_FILE"
    echo -e "其他错误:       $other_errors" | tee -a "$LOG_FILE"
    echo -e "${BLUE}=================================${NC}" | tee -a "$LOG_FILE"
    
    return 0
}

# ========================================================================
# 处理函数：运行QUAST分析
# ========================================================================
run_quast() {
    local quast_total=0
    local quast_success_contigs=0
    local quast_success_scaffolds=0
    local quast_failures=0
    
    log "开始运行QUAST分析..."
    log "输入文件路径: $COPY_TARGET"
    log "QUAST输出路径: $QUAST_OUTPUT"
    
    # 创建QUAST输出目录
    mkdir -p "$QUAST_OUTPUT"
    
    # 处理每个样品
    for dir in "$COPY_TARGET"/*; do
        if [ ! -d "$dir" ]; then
            continue
        fi
        
        local dir_name=$(basename "$dir")
        log "分析样品: $dir_name"
        
        # 处理contigs
        ((quast_total++))
        local contigs_file="$dir/${dir_name}_contigs.fasta"
        local contigs_output="${QUAST_OUTPUT%/}/${dir_name}_contigs_quast_out"
        
        if [ -f "$contigs_file" ]; then
            # 清理旧结果
            if [ -d "$contigs_output" ]; then
                rm -rf "$contigs_output" 2>/dev/null
                log "  清理旧结果: ${dir_name}_contigs_quast_out"
            fi
            
            # 运行QUAST
            local start_time=$(date +%s)
            log "  启动contigs分析: $QUAST_CMD $contigs_file -o $contigs_output"
            
            "$QUAST_CMD" "$contigs_file" -o "$contigs_output" >> "$LOG_FILE" 2>&1
            
            if [ $? -eq 0 ]; then
                local duration=$(( $(date +%s) - start_time ))
                log "  完成contigs分析 (耗时: ${duration}秒)"
                ((quast_success_contigs++))
            else
                log "  ${RED}错误${NC}: contigs分析失败"
                ((quast_failures++))
            fi
        else
            log "  ${RED}错误${NC}: contigs文件缺失"
            ((quast_failures++))
        fi
        
        # 处理scaffolds
        ((quast_total++))
        local scaffolds_file="$dir/${dir_name}_scaffolds.fasta"
        local scaffolds_output="${QUAST_OUTPUT%/}/${dir_name}_scaffolds_quast_out"
        
        if [ -f "$scaffolds_file" ]; then
            # 清理旧结果
            if [ -d "$scaffolds_output" ]; then
                rm -rf "$scaffolds_output" 2>/dev/null
                log "  清理旧结果: ${dir_name}_scaffolds_quast_out"
            fi
            
            # 运行QUAST
            local start_time=$(date +%s)
            log "  启动scaffolds分析: $QUAST_CMD $scaffolds_file -o $scaffolds_output"
            
            "$QUAST_CMD" "$scaffolds_file" -o "$scaffolds_output" >> "$LOG_FILE" 2>&1
            
            if [ $? -eq 0 ]; then
                local duration=$(( $(date +%s) - start_time ))
                log "  完成scaffolds分析 (耗时: ${duration}秒)"
                ((quast_success_scaffolds++))
            else
                log "  ${RED}错误${NC}: scaffolds分析失败"
                ((quast_failures++))
            fi
        else
            log "  ${RED}错误${NC}: scaffolds文件缺失"
            ((quast_failures++))
        fi
    done
    
    # 结果统计
    echo -e "\n${BLUE}========== QUAST分析结果 ==========${NC}" | tee -a "$LOG_FILE"
    echo -e "分析任务总数:       $quast_total" | tee -a "$LOG_FILE"
    echo -e "成功contigs分析:    $quast_success_contigs" | tee -a "$LOG_FILE"
    echo -e "成功scaffolds分析:  $quast_success_scaffolds" | tee -a "$LOG_FILE"
    echo -e "失败分析:          $quast_failures" | tee -a "$LOG_FILE"
    echo -e "${BLUE}=================================${NC}" | tee -a "$LOG_FILE"
    
    return 0
}

# ========================================================================
# 新增函数：固定目录结构运行QUAST（包含完整报告参数）
# ========================================================================
run_fixed_structure_quast() {
    local species_root="$1"
    local quast_output="$2"
    
    local total_species=0
    local processed_species=0
    local missing_files=0
    local quast_failures=0
    
    log "开始处理固定目录结构..."
    log "物种根目录: $species_root"
    log "QUAST输出路径: $quast_output"
    
    # 创建QUAST输出目录
    mkdir -p "$quast_output"
    
    # 检查目录结构
    if [ ! -d "$species_root" ]; then
        log "${RED}错误: 物种根目录不存在${NC}"
        return 1
    fi
    
    # 创建包含所有参数的汇总文件
    local summary_file="${quast_output}/quast_summary_full_${TIMESTAMP}.tsv"
    # 表头行
    echo -e "Species Name\tFile Size\tAssembly Size\tGC (%)\t# contigs (>=0 bp)\t# contigs (>=1000 bp)\t# contigs (>=5000 bp)\t# contigs (>=10000 bp)\t# contigs (>=25000 bp)\t# contigs (>=50000 bp)\tTotal length (>=0 bp)\tTotal length (>=1000 bp)\tTotal length (>=5000 bp)\tTotal length (>=10000 bp)\tTotal length (>=25000 bp)\tTotal length (>=50000 bp)\t# contigs\tLargest contig\tTotal length\tN50\tN90\tauN\tL50\tL90\t# N's per 100 kbp" > "$summary_file"
    
    # 处理每个物种目录
    for species_dir in "$species_root"/*; do
        if [ ! -d "$species_dir" ]; then
            continue
        fi
        
        local species_name=$(basename "$species_dir")
        ((total_species++))
        
        log "处理物种: $species_name"
        
        # 构建文件路径
        local scaffolds_path="$species_dir/kraken/spades/scaffolds.fasta"
        
        # 检查文件是否存在
        if [ ! -f "$scaffolds_path" ]; then
            log "  ${RED}错误${NC}: 文件未找到: $scaffolds_path"
            # 添加空行保持格式
            echo -e "$species_name\tFILE_MISSING\t" >> "$summary_file"
            ((missing_files++))
            continue
        fi
        
        # 创建物种专用输出目录
        local quast_output_dir="${quast_output}/${species_name}_quast"
        
        # 清理旧结果
        if [ -d "$quast_output_dir" ]; then
            rm -rf "$quast_output_dir" 2>/dev/null
            log "  清理旧结果: $quast_output_dir"
        fi
        
        # 运行QUAST
        local start_time=$(date +%s)
        log "  运行QUAST分析: $QUAST_CMD $scaffolds_path -o $quast_output_dir"
        
        "$QUAST_CMD" "$scaffolds_path" -o "$quast_output_dir" >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            local duration=$(( $(date +%s) - start_time ))
            log "  QUAST分析成功 (耗时: ${duration}秒)"
            ((processed_species++))
            
            # 从报告中提取所有指标
            local report_path="$quast_output_dir/report.tsv"
            if [ -f "$report_path" ]; then
                # 提取所有指定指标
                local gc_percent=$(awk -F'\t' '$1 == "GC (%)" {print $2}' "$report_path")
                local contigs_ge_0=$(awk -F'\t' '$1 == "# contigs (>= 0 bp)" {print $2}' "$report_path")
                local contigs_ge_1000=$(awk -F'\t' '$1 == "# contigs (>= 1000 bp)" {print $2}' "$report_path")
                local contigs_ge_5000=$(awk -F'\t' '$1 == "# contigs (>= 5000 bp)" {print $2}' "$report_path")
                local contigs_ge_10000=$(awk -F'\t' '$1 == "# contigs (>= 10000 bp)" {print $2}' "$report_path")
                local contigs_ge_25000=$(awk -F'\t' '$1 == "# contigs (>= 25000 bp)" {print $2}' "$report_path")
                local contigs_ge_50000=$(awk -F'\t' '$1 == "# contigs (>= 50000 bp)" {print $2}' "$report_path")
                local total_length_ge_0=$(awk -F'\t' '$1 == "Total length (>= 0 bp)" {print $2}' "$report_path")
                local total_length_ge_1000=$(awk -F'\t' '$1 == "Total length (>= 1000 bp)" {print $2}' "$report_path")
                local total_length_ge_5000=$(awk -F'\t' '$1 == "Total length (>= 5000 bp)" {print $2}' "$report_path")
                local total_length_ge_10000=$(awk -F'\t' '$1 == "Total length (>= 10000 bp)" {print $2}' "$report_path")
                local total_length_ge_25000=$(awk -F'\t' '$1 == "Total length (>= 25000 bp)" {print $2}' "$report_path")
                local total_length_ge_50000=$(awk -F'\t' '$1 == "Total length (>= 50000 bp)" {print $2}' "$report_path")
                local contigs=$(awk -F'\t' '$1 == "# contigs" {print $2}' "$report_path")
                local largest_contig=$(awk -F'\t' '$1 == "Largest contig" {print $2}' "$report_path")
                local total_length=$(awk -F'\t' '$1 == "Total length" {print $2}' "$report_path")
                local n50=$(awk -F'\t' '$1 == "N50" {print $2}' "$report_path")
                local n90=$(awk -F'\t' '$1 == "N90" {print $2}' "$report_path")
                local aun=$(awk -F'\t' '$1 == "auN" {print $2}' "$report_path")
                local l50=$(awk -F'\t' '$1 == "L50" {print $2}' "$report_path")
                local l90=$(awk -F'\t' '$1 == "L90" {print $2}' "$report_path")
                local ns_per_100kbp=$(awk -F'\t' '$1 == "# N'"'"'s per 100 kbp" {print $2}' "$report_path")
                
                # 获取文件大小
                local file_size=$(ls -lh "$scaffolds_path" | awk '{print $5}')
                
                # 添加到汇总文件
                echo -e "$species_name\t$file_size\t$total_length\t$gc_percent\t$contigs_ge_0\t$contigs_ge_1000\t$contigs_ge_5000\t$contigs_ge_10000\t$contigs_ge_25000\t$contigs_ge_50000\t$total_length_ge_0\t$total_length_ge_1000\t$total_length_ge_5000\t$total_length_ge_10000\t$total_length_ge_25000\t$total_length_ge_50000\t$contigs\t$largest_contig\t$total_length\t$n50\t$n90\t$aun\t$l50\t$l90\t$ns_per_100kbp" >> "$summary_file"
            else
                log "  ${YELLOW}警告${NC}: 未找到QUAST报告文件"
                echo -e "$species_name\tANALYSIS_DONE_BUT_REPORT_MISSING\t" >> "$summary_file"
            fi
        else
            log "  ${RED}错误${NC}: QUAST分析失败"
            echo -e "$species_name\tANALYSIS_FAILED\t" >> "$summary_file"
            ((quast_failures++))
        fi
    done
    
    # 结果统计
    echo -e "\n${BLUE}========== 固定结构QUAST结果 ==========${NC}" | tee -a "$LOG_FILE"
    echo -e "物种总数:        $total_species" | tee -a "$LOG_FILE"
    echo -e "成功分析物种数:  $processed_species" | tee -a "$LOG_FILE"
    echo -e "文件缺失数:      $missing_files" | tee -a "$LOG_FILE"
    echo -e "QUAST失败数:     $quast_failures" | tee -a "$LOG_FILE"
    
    # 输出汇总信息
    if [ -f "$summary_file" ]; then
        echo -e "\n${GREEN}============================ QUAST完整报告已生成 ============================${NC}" | tee -a "$LOG_FILE"
        log "QUAST完整汇总表格已保存: $summary_file"
        log "由于报告包含大量数据，完整报告已输出到表格文件"
        log "您可以使用以下命令查看完整报告:"
        log "  column -t -s $'\t' \"$summary_file\" | less -S"
    else
        log "${YELLOW}警告: 未生成QUAST汇总报告${NC}"
    fi
    
    return 0
}

# ========================================================================
# 主执行流程
# ========================================================================
log "开始处理..."
START_TIME=$(date +%s)

case $MODE in
    1)
        process_spades
        ;;
    2)
        process_spades
        run_quast
        ;;
    3)
        run_fixed_structure_quast "$SPECIES_ROOT" "$QUAST_OUTPUT"
        ;;
esac

# 计算总耗时
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINS=$((DURATION / 60))
SECS=$((DURATION % 60))

# 最终结果
echo -e "\n${GREEN}=============================================${NC}" | tee -a "$LOG_FILE"
echo -e "${GREEN}所有操作完成!${NC}" | tee -a "$LOG_FILE"
echo -e "${GREEN}总耗时: ${MINS}分${SECS}秒${NC}" | tee -a "$LOG_FILE"
echo -e "${GREEN}日志文件: $LOG_FILE${NC}" | tee -a "$LOG_FILE"
if [ "$MODE" = "3" ] && [ -f "$summary_file" ]; then
    echo -e "${GREEN}QUAST完整报告: $summary_file${NC}" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}提示: 由于报告较宽，可以使用以下命令查看:${NC}" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}column -t -s $'\t' \"$summary_file\" | less -S${NC}" | tee -a "$LOG_FILE"
fi
echo -e "${GREEN}=============================================${NC}" | tee -a "$LOG_FILE"
