STRINGS = {
    # === 主菜单 ===
    "app_title": "BioFlow-CLI  生物信息学工作流工具",
    "menu_prompt": "请选择操作：",
    "menu_env": "[环境] 安装生物工具",
    "menu_seq": "[序列] 格式化处理",
    "menu_settings": "[设置] 切换语言",
    "menu_exit": "[退出] 退出程序",

    # === 语言选择 ===
    "lang_prompt": "请选择语言：",
    "lang_saved": "语言偏好已保存。",

    # === 环境管理 ===
    "env_title": "环境管理器",
    "env_select_tool": "请选择要安装的工具：",
    "env_installing": "正在安装 {tool}...",
    "env_install_ok": "{tool} 安装成功。",
    "env_install_fail": "{tool} 安装失败：{err}",
    "env_back": "返回主菜单",
    "env_already": "{tool} 已安装。",
    "env_not_found": "未找到 {tool}，准备安装。",
    "env_checking": "正在检查 {tool} 状态...",

    # === 序列任务 ===
    "seq_title": "序列格式化",
    "seq_input_prompt": "请输入 FASTA 文件路径：",
    "seq_output_prompt": "请输入输出文件路径：",
    "seq_processing": "正在处理序列...",
    "seq_done": "完成！已格式化 {count} 条序列，保存至 {path}。",
    "seq_file_not_found": "文件未找到：{path}",
    "seq_invalid_format": "无效的 FASTA 格式。",
    "seq_back": "返回主菜单",
    "seq_wrap_prompt": "每行字符宽度（默认 80）：",

    # === 通用 ===
    "confirm_exit": "确定要退出吗？",
    "yes": "是",
    "no": "否",
    "goodbye": "再见！",
    "error_unexpected": "发生意外错误：{err}",
    "press_enter": "按 Enter 键继续...",
    "env_conda_missing": "未检测到 Conda，请先安装 Conda（https://docs.conda.io/）。",
    "seq_large_file_warn": "警告：文件大小为 {size} MB，可能占用大量内存。",
}
