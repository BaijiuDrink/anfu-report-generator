#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
import yaml

from vuln_manager import VulnManager, create_finding, RISK_LEVELS
from report_builder import ReportBuilder

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DEFAULT_LIBRARY = os.path.join(BASE_DIR, "vuln_library", "default_vulns.json")


def _resolve_output_path(user_output, project_name):
    filename = user_output or f"{project_name}_渗透测试报告.docx"
    if not filename.endswith(".docx"):
        filename += ".docx"
    if os.path.isabs(filename):
        return filename
    if os.path.dirname(filename):
        return os.path.join(BASE_DIR, filename)
    return os.path.join(DEFAULT_OUTPUT_DIR, filename)


def _banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║              渗透测试报告生成工具  v1.0                       ║
║          Pentest Report Generator                            ║
╚══════════════════════════════════════════════════════════════╝
""")


def _select_vuln_interactive(vuln_manager):
    vulns = vuln_manager.list_all()
    if not vulns:
        print("[提示] 漏洞库为空，请先添加漏洞或使用自定义模式\n")
        return None

    print("\n漏洞库列表:")
    print("-" * 70)
    print(f'{"#":<4}{"ID":<14}{"名称":<24}{"分类":<12}{"风险等级"}')
    print("-" * 70)
    for i, v in enumerate(vulns):
        print(
            f'{i + 1:<4}{v.get("id", ""):<14}{v.get("name", ""):<24}{v.get("category", ""):<12}{v.get("risk_level", "")}'
        )
    print("-" * 70)
    print(f"共 {len(vulns)} 条漏洞记录")

    print("\n操作: 输入编号选择漏洞 / 输入关键词搜索 / 输入 q 自定义漏洞")
    while True:
        choice = input("> ").strip()
        if choice.lower() == "q":
            return None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(vulns):
                return vulns[idx]
            print("编号超出范围，请重新输入")
        else:
            results = vuln_manager.search(choice)
            if results:
                print(f"\n搜索结果 ({len(results)} 条):")
                for i, v in enumerate(results):
                    print(
                        f'  [{i + 1}] {v.get("id")} - {v.get("name")} ({v.get("risk_level")})'
                    )
                sub = input("选择编号 (回车取消): ").strip()
                if sub.isdigit():
                    sidx = int(sub) - 1
                    if 0 <= sidx < len(results):
                        return results[sidx]
            else:
                print(f'未找到与 "{choice}" 相关的漏洞')


def _input_finding_interactive(vuln_manager):
    print("\n--- 录入漏洞信息 ---")
    vuln_template = _select_vuln_interactive(vuln_manager)

    finding = {}
    if vuln_template:
        finding["vuln_id"] = vuln_template["id"]
        finding["name"] = (
            input(f'漏洞名称 [{vuln_template["name"]}]: ').strip()
            or vuln_template["name"]
        )
        finding["risk_level"] = (
            input(f'风险等级 [{vuln_template["risk_level"]}]: ').strip()
            or vuln_template["risk_level"]
        )
        use_default_desc = input("使用漏洞库默认描述? (Y/n): ").strip().lower()
        if use_default_desc in ("n", "no"):
            finding["description"] = input("漏洞描述 (可多行，输入空行结束):\n")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            if lines:
                finding["description"] = "\n".join([finding["description"]] + lines)
            else:
                finding["description"] = vuln_template.get("description", "")
        else:
            finding["description"] = vuln_template.get("description", "")
        use_default_fix = input("使用漏洞库默认修复建议? (Y/n): ").strip().lower()
        if use_default_fix in ("n", "no"):
            finding["fix_suggestion"] = input("修复建议 (可多行，输入空行结束):\n")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            if lines:
                finding["fix_suggestion"] = "\n".join(
                    [finding["fix_suggestion"]] + lines
                )
            else:
                finding["fix_suggestion"] = vuln_template.get("fix_suggestion", "")
        else:
            finding["fix_suggestion"] = vuln_template.get("fix_suggestion", "")
    else:
        finding["name"] = input("漏洞名称: ").strip()
        if not finding["name"]:
            print("[错误] 漏洞名称不能为空")
            return None
        finding["risk_level"] = (
            input(f'风险等级 ({"/".join(RISK_LEVELS)}): ').strip() or "中危"
        )
        finding["description"] = input("漏洞描述: ").strip()
        finding["fix_suggestion"] = input("修复建议: ").strip()

    finding["url"] = input("漏洞地址/URL: ").strip()
    finding["screenshot"] = input("漏洞验证截图路径 (可留空): ").strip()

    return finding


def run_interactive_mode(args):
    _banner()
    vuln_manager = VulnManager(args.library)

    project_name = input("项目名称 (如 XX公司渗透测试): ").strip() or "渗透测试报告"

    findings = []
    print(f"\n开始录入 {project_name} 的漏洞发现...")

    while True:
        finding = _input_finding_interactive(vuln_manager)
        if finding:
            findings.append(finding)
            print(f'[已录入] {finding["name"]} ({finding["risk_level"]})')
            print(f"当前已录入 {len(findings)} 个漏洞\n")

        cont = input("继续添加漏洞? (Y/n): ").strip().lower()
        if cont in ("n", "no"):
            break

    if not findings:
        print("\n[退出] 未录入任何漏洞，报告未生成")
        sys.exit(0)

    output_filename = _resolve_output_path(args.output, project_name)

    print(f"\n正在生成报告: {output_filename}")
    builder = ReportBuilder(project_name=project_name)
    builder.add_summary_section(findings)
    builder.add_findings_section(findings)
    builder.save(output_filename)
    print(f"\n[完成] 报告已保存至: {output_filename}")


def run_config_mode(args):
    config_path = args.config
    with open(config_path, "r", encoding="utf-8") as f:
        if config_path.endswith(".yaml") or config_path.endswith(".yml"):
            config = yaml.safe_load(f)
        else:
            config = json.load(f)

    project_name = config.get("project_name", "渗透测试报告")
    findings_input = config.get("findings", [])

    if not findings_input:
        print("[错误] 配置文件中未包含 findings 字段")
        sys.exit(1)

    vuln_manager = VulnManager(args.library)
    findings = []

    for item in findings_input:
        f = create_finding(
            vuln_manager,
            vuln_id=item.get("vuln_id"),
            url=item.get("url", ""),
            custom_name=item.get("name"),
            custom_description=item.get("description"),
            custom_risk_level=item.get("risk_level"),
            custom_fix_suggestion=item.get("fix_suggestion"),
            verify_steps=item.get("verify_steps"),
            verify_result=item.get("verify_result"),
            fix_priority=item.get("fix_priority"),
            fix_verify=item.get("fix_verify"),
            network_zone=item.get("network_zone", "互联网"),
            host_ip=item.get("host_ip", ""),
        )
        findings.append(f)
        print(f'[已加载] {f["name"]} ({f["risk_level"]})')

    output_filename = _resolve_output_path(args.output, project_name)

    print(f"\n正在生成报告: {output_filename}")
    builder = ReportBuilder(project_name=project_name)
    builder.add_summary_section(findings)
    builder.add_findings_section(findings)
    builder.save(output_filename)
    print(f"\n[完成] 报告已保存至: {output_filename}")


def run_library_list(args):
    vm = VulnManager(args.library)
    vulns = vm.list_all()
    if not vulns:
        print("漏洞库为空")
        return
    print(f"\n漏洞库路径: {vm.get_library_path()}")
    print(f"共 {len(vulns)} 条漏洞记录:\n")
    for v in vulns:
        print(
            f'  [{v.get("id")}] {v.get("name")} | {v.get("category")} | {v.get("risk_level")}'
        )
    print("")


def run_library_add(args):
    vm = VulnManager(args.library)
    print("输入新漏洞信息 (直接回车跳过):")
    vuln = {}
    vuln["id"] = input("漏洞ID (如 SQL-002): ").strip()
    if not vuln["id"]:
        print("[取消] ID不能为空")
        return
    vuln["name"] = input("漏洞名称: ").strip()
    vuln["category"] = input("漏洞分类: ").strip()
    vuln["risk_level"] = (
        input(f'风险等级 ({"/".join(RISK_LEVELS)}): ').strip() or "中危"
    )
    vuln["description"] = input("漏洞描述: ").strip()
    vuln["fix_suggestion"] = input("修复建议: ").strip()
    try:
        vm.add(vuln)
        print(f'[已添加] {vuln["id"]} - {vuln["name"]}')
    except ValueError as e:
        print(f"[错误] {e}")


def run_library_edit(args):
    vm = VulnManager(args.library)
    vuln_id = args.edit_id
    existing = vm.get_by_id(vuln_id)
    if not existing:
        print(f"[错误] 漏洞ID [{vuln_id}] 不存在")
        return
    print(f"编辑漏洞 [{vuln_id}] (直接回车保留原值):")
    updates = {}
    name = input(f'名称 [{existing.get("name")}]: ').strip()
    if name:
        updates["name"] = name
    category = input(f'分类 [{existing.get("category")}]: ').strip()
    if category:
        updates["category"] = category
    risk = input(f'风险等级 [{existing.get("risk_level")}]: ').strip()
    if risk:
        updates["risk_level"] = risk
    desc = input(f'描述 [{existing.get("description", "")[:30]}...]: ').strip()
    if desc:
        updates["description"] = desc
    fix = input(f'修复建议 [{existing.get("fix_suggestion", "")[:30]}...]: ').strip()
    if fix:
        updates["fix_suggestion"] = fix
    if updates:
        vm.update(vuln_id, updates)
        print(f"[已更新] {vuln_id}")
    else:
        print("[未修改]")


def run_library_delete(args):
    vm = VulnManager(args.library)
    vuln_id = args.delete_id
    existing = vm.get_by_id(vuln_id)
    if not existing:
        print(f"[错误] 漏洞ID [{vuln_id}] 不存在")
        return
    confirm = (
        input(f'确认删除 [{vuln_id}] {existing.get("name")}? (y/N): ').strip().lower()
    )
    if confirm == "y":
        vm.delete(vuln_id)
        print(f"[已删除] {vuln_id}")
    else:
        print("[已取消]")


def run_init_config(args):
    config_path = args.output or "report_config_sample.json"
    sample = {
        "project_name": "示例项目渗透测试",
        "findings": [
            {
                "vuln_id": "SQL-001",
                "url": "https://example.com/login?user=admin",
                "network_zone": "互联网",
                "verify_steps": "1. 使用BurpSuite拦截登录请求\n2. 替换Payload: admin' OR '1'='1\n3. 成功绕过认证",
                "verify_result": "成功绕过身份认证，获取管理员权限",
                "fix_priority": "紧急",
                "fix_verify": "使用原Payload重新测试，确认漏洞已修复",
            },
            {
                "vuln_id": "XSS-001",
                "url": "https://example.com/search?q=xss",
                "network_zone": "互联网",
                "fix_priority": "高",
            },
            {
                "vuln_id": "PASS-001",
                "url": "10.0.0.1",
                "host_ip": "10.0.0.1",
                "network_zone": "内网",
                "fix_priority": "高",
            },
            {
                "vuln_id": "PASS-001",
                "url": "10.0.0.2",
                "host_ip": "10.0.0.2",
                "network_zone": "内网",
                "fix_priority": "高",
            },
            {
                "name": "自定义漏洞示例",
                "url": "https://example.com/admin",
                "risk_level": "高危",
                "network_zone": "互联网",
                "description": "这是一个直接自定义的漏洞，未引用漏洞库",
                "fix_suggestion": "对应的修复建议",
                "fix_priority": "高",
            },
        ],
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=2)
    print(f"[已生成] 示例配置文件: {config_path}")


def main():
    parser = argparse.ArgumentParser(
        description="渗透测试报告生成工具 - 图形化/CLI双模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 图形化模式 (推荐)
  python report_generator.py --gui

  # 交互式CLI模式
  python report_generator.py

  # 从配置文件一键生成报告
  python report_generator.py -c findings.json

  # 查看漏洞库
  python report_generator.py --list

  # 添加漏洞到库
  python report_generator.py --add

  # 编辑漏洞库中的漏洞
  python report_generator.py --edit SQL-001

  # 删除漏洞库中的漏洞
  python report_generator.py --delete SQL-001

  # 生成示例配置文件
  python report_generator.py --init-config
        """,
    )

    parser.add_argument(
        "-c", "--config", help="配置文件路径 (JSON/YAML)，从配置文件生成报告"
    )
    parser.add_argument(
        "-o", "--output", help="输出文件路径 (默认: output/项目名称_渗透测试报告.docx)"
    )
    parser.add_argument(
        "-l", "--library", default=DEFAULT_LIBRARY, help="漏洞库文件路径"
    )
    parser.add_argument("--gui", action="store_true", help="启动图形化界面")

    sub = parser.add_mutually_exclusive_group()
    sub.add_argument("--list", action="store_true", help="列出漏洞库所有漏洞")
    sub.add_argument("--add", action="store_true", help="交互式添加新漏洞到漏洞库")
    sub.add_argument("--edit", dest="edit_id", metavar="ID", help="编辑指定ID的漏洞")
    sub.add_argument(
        "--delete", dest="delete_id", metavar="ID", help="删除指定ID的漏洞"
    )
    sub.add_argument("--init-config", action="store_true", help="生成示例配置文件")

    args = parser.parse_args()

    if args.gui:
        from gui_app import main as gui_main

        gui_main()
    elif args.list:
        run_library_list(args)
    elif args.add:
        run_library_add(args)
    elif args.edit_id:
        run_library_edit(args)
    elif args.delete_id:
        run_library_delete(args)
    elif args.init_config:
        run_init_config(args)
    elif args.config:
        run_config_mode(args)
    else:
        run_interactive_mode(args)


if __name__ == "__main__":
    main()
