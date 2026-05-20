#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import io
import struct
import re
import base64
import html as html_mod
import ctypes
import json
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import ImageGrab, Image, ImageTk
import win32clipboard

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from vuln_manager import (
    VulnManager,
    FIX_PRIORITIES,
    NETWORK_ZONES,
    batch_create_findings,
)
from report_builder import ReportBuilder

DEFAULT_LIBRARY = os.path.join(BASE_DIR, "vuln_library", "default_vulns.json")
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")

RISK_LEVELS_SHORT = ["严重", "高危", "中危", "低危", "信息"]


class PentestReportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("渗透测试报告生成工具 v2.0")
        self.root.geometry("1280x820")
        self.root.minsize(1100, 700)

        self.vuln_manager = VulnManager(DEFAULT_LIBRARY)
        self.findings = []
        self.current_edit_idx = -1

        self.screenshots_dir = os.path.join(BASE_DIR, "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)
        self._paste_images = []

        self._setup_styles()
        self._build_ui()
        self._refresh_library_list()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Title.TLabel", font=("微软雅黑", 16, "bold"), foreground="#2F5496"
        )
        style.configure(
            "Section.TLabel", font=("微软雅黑", 11, "bold"), foreground="#333333"
        )
        style.configure("Library.Treeview", rowheight=24, font=("微软雅黑", 9))
        style.configure("Finding.Treeview", rowheight=22, font=("微软雅黑", 9))

    def _build_ui(self):
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self._build_top_bar()
        self._build_main_area()

    def _build_top_bar(self):
        top = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        top.grid(row=0, column=0, sticky="ew")

        ttk.Label(top, text="渗透测试报告生成工具", style="Title.TLabel").pack(
            side=tk.LEFT, padx=(0, 20)
        )

        ttk.Label(top, text="项目名称:").pack(side=tk.LEFT, padx=(10, 4))
        self.project_var = tk.StringVar(value="XXX公司渗透测试")
        ttk.Entry(
            top, textvariable=self.project_var, width=30, font=("微软雅黑", 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(top, text="新建项目", command=self._clear_findings).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(top, text="加载配置", command=self._load_config).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(top, text="保存配置", command=self._save_config).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(top, text="批量录入", command=self._batch_add_dialog).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(top, text="生成报告", command=self._generate_report).pack(
            side=tk.LEFT, padx=4
        )

    def _build_main_area(self):
        self.main_pane = tk.PanedWindow(
            self.root, orient=tk.HORIZONTAL, sashwidth=5, sashrelief=tk.RAISED
        )
        self.main_pane.grid(row=1, column=0, sticky="nsew")

        left = self._build_left_panel_in(self.main_pane)
        right = self._build_right_panel_in()

        self.main_pane.add(left, minsize=220, width=280)
        self.main_pane.add(right, minsize=550, stretch="always")

    # ── Left Panel: Vuln Library ──
    def _build_left_panel_in(self, parent):
        left = ttk.Frame(parent, padding=(8, 4, 4, 8))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ttk.Label(left, text="漏洞库", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )

        search_frame = ttk.Frame(left)
        search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self.search_var = tk.StringVar()
        ttk.Entry(
            search_frame, textvariable=self.search_var, width=22, font=("微软雅黑", 9)
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            search_frame, text="搜索", command=self._search_library, width=5
        ).pack(side=tk.LEFT, padx=(2, 0))
        self.search_var.trace_add("write", lambda *a: self._search_library())

        columns = ("name", "risk", "category")
        self.lib_tree = ttk.Treeview(
            left, columns=columns, show="headings", height=20, style="Library.Treeview"
        )
        self.lib_tree.heading("name", text="漏洞名称")
        self.lib_tree.heading("risk", text="等级")
        self.lib_tree.heading("category", text="分类")
        self.lib_tree.column("name", width=180, minwidth=120)
        self.lib_tree.column("risk", width=50, anchor="center")
        self.lib_tree.column("category", width=70, anchor="center")
        self.lib_tree.grid(row=2, column=0, sticky="nsew")

        lib_scroll = ttk.Scrollbar(
            left, orient=tk.VERTICAL, command=self.lib_tree.yview
        )
        lib_scroll.grid(row=2, column=1, sticky="ns")
        self.lib_tree.configure(yscrollcommand=lib_scroll.set)

        self.lib_tree.bind("<Double-1>", self._on_library_double_click)
        self.lib_tree.bind("<ButtonRelease-1>", self._on_library_select)

        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ttk.Button(btn_frame, text="添加到项目", command=self._add_from_library).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(
            btn_frame, text="管理漏洞库", command=self._open_library_manager
        ).pack(side=tk.LEFT, padx=2)

        left.grid_rowconfigure(4, weight=1)
        self.lib_preview_text = tk.Text(
            left, height=8, font=("微软雅黑", 9), wrap=tk.WORD, state="disabled"
        )
        self.lib_preview_text.grid(
            row=4, column=0, columnspan=2, sticky="nsew", pady=(4, 0)
        )

        return left

    def _refresh_library_list(self, vulns=None):
        for item in self.lib_tree.get_children():
            self.lib_tree.delete(item)
        if vulns is None:
            vulns = self.vuln_manager.list_all()
        for v in vulns:
            self.lib_tree.insert(
                "",
                tk.END,
                values=(
                    v.get("name", ""),
                    v.get("risk_level", ""),
                    v.get("category", ""),
                ),
                tags=(v.get("id", ""),),
            )

    def _search_library(self):
        kw = self.search_var.get().strip()
        if not kw:
            self._refresh_library_list()
        else:
            results = self.vuln_manager.search(kw)
            self._refresh_library_list(results)

    def _get_selected_library_vuln(self):
        sel = self.lib_tree.selection()
        if not sel:
            return None
        tags = self.lib_tree.item(sel[0], "tags")
        vuln_id = tags[0] if tags else None
        if vuln_id:
            return self.vuln_manager.get_by_id(vuln_id)
        return None

    def _on_library_select(self, event):
        v = self._get_selected_library_vuln()
        if v:
            self._preview_library_vuln(v)

    def _on_library_double_click(self, event):
        self._add_from_library()

    def _preview_library_vuln(self, vuln):
        text = (
            f"ID: {vuln.get('id', '')}\n"
            f"名称: {vuln.get('name', '')}\n"
            f"分类: {vuln.get('category', '')}  |  风险等级: {vuln.get('risk_level', '')}\n"
            f"────────────────────────────────────\n"
            f"描述:\n{vuln.get('description', '无')[:200]}\n\n"
            f"修复建议:\n{vuln.get('fix_suggestion', '无')[:200]}"
        )
        self.lib_preview_text.configure(state="normal")
        self.lib_preview_text.delete("1.0", tk.END)
        self.lib_preview_text.insert("1.0", text)
        self.lib_preview_text.configure(state="disabled")

    def _add_from_library(self):
        v = self._get_selected_library_vuln()
        if not v:
            messagebox.showinfo("提示", "请先在漏洞库中选择一个漏洞")
            return
        self._show_editor(finding_template=v)

    # ── Right Panel: Findings + Editor ──
    def _build_right_panel_in(self):
        right = ttk.Frame(self.main_pane, padding=(4, 4, 8, 4))
        right.grid_rowconfigure(0, weight=0)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ttk.Label(right, text="已录入漏洞列表", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        f_btn_frame = ttk.Frame(right)
        f_btn_frame.grid(row=0, column=0, sticky="e")
        ttk.Button(
            f_btn_frame, text="↑上移", command=lambda: self._move_finding(-1), width=5
        ).pack(side=tk.LEFT, padx=1)
        ttk.Button(
            f_btn_frame, text="↓下移", command=lambda: self._move_finding(1), width=5
        ).pack(side=tk.LEFT, padx=1)
        ttk.Button(f_btn_frame, text="编辑", command=self._edit_finding, width=5).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(f_btn_frame, text="复制", command=self._copy_finding, width=5).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(
            f_btn_frame, text="×删除", command=self._delete_finding, width=5
        ).pack(side=tk.LEFT, padx=1)

        self.right_pane = tk.PanedWindow(
            right, orient=tk.VERTICAL, sashwidth=5, sashrelief=tk.RAISED
        )
        self.right_pane.grid(row=1, column=0, sticky="nsew", pady=(2, 0))

        findings_frame = self._build_findings_list()
        editor_frame = self._build_editor_panel_in()

        self.right_pane.add(findings_frame, minsize=100, height=140, stretch="always")
        self.right_pane.add(editor_frame, minsize=250, stretch="always")

        return right

    def _build_findings_list(self):
        list_frame = ttk.Frame(self.right_pane)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        f_columns = ("idx", "zone", "name", "risk", "url", "priority")
        self.findings_tree = ttk.Treeview(
            list_frame,
            columns=f_columns,
            show="headings",
            height=5,
            style="Finding.Treeview",
        )
        self.findings_tree.heading("idx", text="#")
        self.findings_tree.heading("zone", text="区域")
        self.findings_tree.heading("name", text="漏洞名称")
        self.findings_tree.heading("risk", text="风险等级")
        self.findings_tree.heading("url", text="漏洞地址")
        self.findings_tree.heading("priority", text="优先级")
        self.findings_tree.column("idx", width=30, anchor="center")
        self.findings_tree.column("zone", width=45, anchor="center")
        self.findings_tree.column("name", width=160)
        self.findings_tree.column("risk", width=55, anchor="center")
        self.findings_tree.column("url", width=260)
        self.findings_tree.column("priority", width=55, anchor="center")
        self.findings_tree.grid(row=0, column=0, sticky="nsew")

        f_scroll = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.findings_tree.yview
        )
        f_scroll.grid(row=0, column=1, sticky="ns")
        self.findings_tree.configure(yscrollcommand=f_scroll.set)
        self.findings_tree.bind("<Double-1>", self._on_finding_double_click)

        return list_frame

    def _build_editor_panel_in(self):
        editor_frame = ttk.LabelFrame(
            self.right_pane, text="漏洞编辑区", padding=(8, 4, 8, 8)
        )
        editor_frame.grid_columnconfigure(0, weight=0)
        editor_frame.grid_columnconfigure(1, weight=1)

        text_rows = [1, 5, 6, 7, 8, 9]
        for r in text_rows:
            editor_frame.grid_rowconfigure(r, weight=1)

        row = 0
        ttk.Label(editor_frame, text="漏洞名称:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=1
        )
        self.editor_name = tk.StringVar()
        ttk.Entry(
            editor_frame, textvariable=self.editor_name, font=("微软雅黑", 9)
        ).grid(row=row, column=1, sticky="ew", pady=1, padx=(4, 0))

        row = 1
        ttk.Label(editor_frame, text="漏洞地址:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="nw", pady=1
        )
        self.editor_url = tk.Text(
            editor_frame, height=3, font=("微软雅黑", 9), wrap=tk.WORD
        )
        self.editor_url.grid(row=row, column=1, sticky="nsew", pady=1, padx=(4, 0))

        row = 2
        ttk.Label(editor_frame, text="网络区域:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=1
        )
        zone_frame = ttk.Frame(editor_frame)
        zone_frame.grid(row=row, column=1, sticky="w", pady=1, padx=(4, 0))
        self.editor_zone = tk.StringVar(value="互联网")
        for z in NETWORK_ZONES:
            ttk.Radiobutton(
                zone_frame, text=z, value=z, variable=self.editor_zone
            ).pack(side=tk.LEFT, padx=2)

        row = 3
        ttk.Label(editor_frame, text="风险等级:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=1
        )
        risk_frame = ttk.Frame(editor_frame)
        risk_frame.grid(row=row, column=1, sticky="w", pady=1, padx=(4, 0))
        self.editor_risk = tk.StringVar(value="中危")
        for r in RISK_LEVELS_SHORT:
            ttk.Radiobutton(
                risk_frame, text=r, value=r, variable=self.editor_risk
            ).pack(side=tk.LEFT, padx=2)

        row = 4
        ttk.Label(editor_frame, text="修复优先级:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=1
        )
        pri_frame = ttk.Frame(editor_frame)
        pri_frame.grid(row=row, column=1, sticky="w", pady=1, padx=(4, 0))
        self.editor_priority = tk.StringVar(value="高")
        for p in FIX_PRIORITIES:
            ttk.Radiobutton(
                pri_frame, text=p, value=p, variable=self.editor_priority
            ).pack(side=tk.LEFT, padx=2)

        row = 5
        ttk.Label(editor_frame, text="漏洞描述:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="nw", pady=1
        )
        self.editor_description = tk.Text(
            editor_frame, height=3, font=("微软雅黑", 9), wrap=tk.WORD
        )
        self.editor_description.grid(
            row=row, column=1, sticky="nsew", pady=1, padx=(4, 0)
        )

        row = 6
        ttk.Label(editor_frame, text="漏洞验证:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="nw", pady=1
        )
        self.editor_verify_steps = tk.Text(
            editor_frame, height=8, font=("微软雅黑", 9), wrap=tk.WORD
        )
        self.editor_verify_steps.grid(
            row=row, column=1, sticky="nsew", pady=1, padx=(4, 0)
        )
        self._bind_paste_handler(self.editor_verify_steps)

        row = 7
        ttk.Label(editor_frame, text="验证结果:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="nw", pady=1
        )
        self.editor_verify_result = tk.Text(
            editor_frame, height=2, font=("微软雅黑", 9), wrap=tk.WORD
        )
        self.editor_verify_result.grid(
            row=row, column=1, sticky="nsew", pady=1, padx=(4, 0)
        )

        row = 8
        ttk.Label(editor_frame, text="修复建议:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="nw", pady=1
        )
        self.editor_fix_suggestion = tk.Text(
            editor_frame, height=3, font=("微软雅黑", 9), wrap=tk.WORD
        )
        self.editor_fix_suggestion.grid(
            row=row, column=1, sticky="nsew", pady=1, padx=(4, 0)
        )

        row = 9
        ttk.Label(
            editor_frame, text="整改验证方法:", font=("微软雅黑", 9, "bold")
        ).grid(row=row, column=0, sticky="nw", pady=1)
        self.editor_fix_verify = tk.Text(
            editor_frame, height=2, font=("微软雅黑", 9), wrap=tk.WORD
        )
        self.editor_fix_verify.grid(
            row=row, column=1, sticky="nsew", pady=1, padx=(4, 0)
        )

        row = 10
        btn_row = ttk.Frame(editor_frame)
        btn_row.grid(row=row, column=0, columnspan=2, sticky="e", pady=(4, 0))
        ttk.Button(btn_row, text="✓ 保存漏洞", command=self._save_current_finding).pack(
            side=tk.RIGHT, padx=2
        )
        ttk.Button(btn_row, text="清空表单", command=self._clear_editor).pack(
            side=tk.RIGHT, padx=2
        )

        self.editor_template_id = None
        return editor_frame

    def _show_editor(self, finding_template=None):
        self._clear_editor()
        if finding_template:
            self.editor_template_id = finding_template.get("id")
            self.editor_name.set(finding_template.get("name", ""))
            self.editor_description.insert(
                "1.0", finding_template.get("description", "")
            )
            self.editor_risk.set(finding_template.get("risk_level", "中危"))
            self.editor_verify_steps.insert(
                "1.0", finding_template.get("verify_steps", "")
            )
            self.editor_verify_result.insert(
                "1.0", finding_template.get("verify_result", "")
            )
            self.editor_fix_suggestion.insert(
                "1.0", finding_template.get("fix_suggestion", "")
            )
            self.editor_priority.set(finding_template.get("fix_priority", "高"))
            self.editor_fix_verify.insert("1.0", finding_template.get("fix_verify", ""))

    def _clear_editor(self):
        self.editor_template_id = None
        self.current_edit_idx = -1
        self.editor_name.set("")
        self.editor_url.delete("1.0", tk.END)
        self.editor_zone.set("互联网")
        self.editor_risk.set("中危")
        self.editor_priority.set("高")
        for w in [
            self.editor_description,
            self.editor_verify_steps,
            self.editor_verify_result,
            self.editor_fix_suggestion,
            self.editor_fix_verify,
        ]:
            w.delete("1.0", tk.END)

    def _get_editor_data(self):
        return {
            "name": self.editor_name.get().strip(),
            "url": self.editor_url.get("1.0", tk.END).strip(),
            "network_zone": self.editor_zone.get(),
            "risk_level": self.editor_risk.get(),
            "description": self.editor_description.get("1.0", tk.END).strip(),
            "verify_steps": self.editor_verify_steps.get("1.0", tk.END).strip(),
            "verify_result": self.editor_verify_result.get("1.0", tk.END).strip(),
            "fix_suggestion": self.editor_fix_suggestion.get("1.0", tk.END).strip(),
            "fix_priority": self.editor_priority.get(),
            "fix_verify": self.editor_fix_verify.get("1.0", tk.END).strip(),
            "vuln_id": self.editor_template_id,
        }

    def _set_editor_data(self, finding):
        self.editor_template_id = finding.get("vuln_id")
        self.editor_name.set(finding.get("name", ""))
        self.editor_url.delete("1.0", tk.END)
        self.editor_url.insert("1.0", finding.get("url", ""))
        self.editor_zone.set(finding.get("network_zone", "互联网"))
        self.editor_risk.set(finding.get("risk_level", "中危"))
        self.editor_priority.set(finding.get("fix_priority", "高"))
        texts = {
            self.editor_description: finding.get("description", ""),
            self.editor_verify_steps: finding.get("verify_steps", ""),
            self.editor_verify_result: finding.get("verify_result", ""),
            self.editor_fix_suggestion: finding.get("fix_suggestion", ""),
            self.editor_fix_verify: finding.get("fix_verify", ""),
        }
        for w, val in texts.items():
            w.delete("1.0", tk.END)
            if w is self.editor_verify_steps:
                self._insert_with_images(w, val)
            else:
                w.insert("1.0", val)

    def _insert_with_images(self, text_widget, content):
        import re

        pattern = re.compile(
            r"\[截图:\s*(screenshots/[^\]]+\.(?:png|jpg|jpeg|gif|bmp))\]", re.IGNORECASE
        )
        last_end = 0
        for m in pattern.finditer(content):
            text_before = content[last_end: m.start()]
            if text_before:
                text_widget.insert(tk.INSERT, text_before)
            rel_path = m.group(1)
            filepath = os.path.join(BASE_DIR, rel_path)
            if os.path.exists(filepath):
                try:
                    img = Image.open(filepath)
                    photo = ImageTk.PhotoImage(img)
                    self._paste_images.append(photo)
                    text_widget.insert(tk.INSERT, "\n")
                    text_widget.image_create(tk.INSERT, image=photo)
                    text_widget.insert(tk.INSERT, "\n")
                except Exception:
                    pass
            text_widget.insert(tk.INSERT, m.group(0))
            last_end = m.end()
        remaining = content[last_end:]
        if remaining:
            text_widget.insert(tk.INSERT, remaining)

    def _save_current_finding(self):
        data = self._get_editor_data()
        if not data["name"]:
            messagebox.showwarning("警告", "漏洞名称不能为空")
            return

        if self.current_edit_idx >= 0:
            self.findings[self.current_edit_idx] = data
        else:
            self.findings.append(data)

        self._refresh_findings_list()
        self._clear_editor()
        messagebox.showinfo("提示", f'漏洞 "{data["name"]}" 已保存')

    def _refresh_findings_list(self):
        for item in self.findings_tree.get_children():
            self.findings_tree.delete(item)
        for i, f in enumerate(self.findings):
            self.findings_tree.insert(
                "",
                tk.END,
                values=(
                    i + 1,
                    f.get("network_zone", "互联网"),
                    f.get("name", ""),
                    f.get("risk_level", ""),
                    f.get("url", "")[:50],
                    f.get("fix_priority", ""),
                ),
            )

    def _on_finding_double_click(self, event):
        self._edit_finding()

    def _edit_finding(self):
        sel = self.findings_tree.selection()
        if not sel:
            return
        values = self.findings_tree.item(sel[0], "values")
        idx = int(values[0]) - 1
        if 0 <= idx < len(self.findings):
            self.current_edit_idx = idx
            self._set_editor_data(self.findings[idx])

    def _delete_finding(self):
        sel = self.findings_tree.selection()
        if not sel:
            return
        values = self.findings_tree.item(sel[0], "values")
        idx = int(values[0]) - 1
        name = self.findings[idx].get("name", "")
        if messagebox.askyesno("确认删除", f'确认删除漏洞 "{name}"?'):
            self.findings.pop(idx)
            self._refresh_findings_list()
            if self.current_edit_idx == idx:
                self._clear_editor()

    def _move_finding(self, direction):
        sel = self.findings_tree.selection()
        if not sel:
            return
        values = self.findings_tree.item(sel[0], "values")
        idx = int(values[0]) - 1
        new_idx = idx + direction
        if 0 <= new_idx < len(self.findings):
            self.findings[idx], self.findings[new_idx] = (
                self.findings[new_idx],
                self.findings[idx],
            )
            self._refresh_findings_list()
            children = self.findings_tree.get_children()
            if new_idx < len(children):
                self.findings_tree.selection_set(children[new_idx])

    def _copy_finding(self):
        sel = self.findings_tree.selection()
        if not sel:
            return
        values = self.findings_tree.item(sel[0], "values")
        idx = int(values[0]) - 1
        if 0 <= idx < len(self.findings):
            import copy

            new_f = copy.deepcopy(self.findings[idx])
            new_name = new_f.get("name", "")
            if not new_name.endswith("(副本)"):
                new_f["name"] = new_f.get("name", "") + " (副本)"
            self.findings.insert(idx + 1, new_f)
            self._refresh_findings_list()
            children = self.findings_tree.get_children()
            if idx + 1 < len(children):
                self.findings_tree.selection_set(children[idx + 1])
                self.current_edit_idx = idx + 1
                self._set_editor_data(new_f)

    def _batch_add_dialog(self):
        v = self._get_selected_library_vuln()
        if v:
            initial_id = v.get("id", "")
        else:
            initial_id = ""

        dialog = tk.Toplevel(self.root)
        dialog.title("批量录入漏洞")
        dialog.geometry("520x420")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frm = ttk.Frame(dialog, padding=(12, 10, 12, 10))
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="漏洞库ID:", font=("微软雅黑", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=2
        )
        id_var = tk.StringVar(value=initial_id)
        ttk.Entry(frm, textvariable=id_var, font=("微软雅黑", 9), width=25).grid(
            row=0, column=1, sticky="w", padx=(8, 0), pady=2
        )

        ttk.Label(frm, text="网络区域:", font=("微软雅黑", 9, "bold")).grid(
            row=1, column=0, sticky="w", pady=2
        )
        zone_var = tk.StringVar(value="内网")
        zf = ttk.Frame(frm)
        zf.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=2)
        for z in NETWORK_ZONES:
            ttk.Radiobutton(zf, text=z, value=z, variable=zone_var).pack(
                side=tk.LEFT, padx=4
            )

        ttk.Label(
            frm, text="主机列表\n(一行一个IP/URL):", font=("微软雅黑", 9, "bold")
        ).grid(row=2, column=0, sticky="nw", pady=2)
        hosts_text = tk.Text(frm, height=8, font=("微软雅黑", 9), wrap=tk.WORD)
        hosts_text.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=2)

        ttk.Label(
            frm, text="自定义名称\n(留空则用漏洞库名):", font=("微软雅黑", 9, "bold")
        ).grid(row=3, column=0, sticky="nw", pady=2)
        name_var = tk.StringVar()
        ttk.Entry(frm, textvariable=name_var, font=("微软雅黑", 9), width=25).grid(
            row=3, column=1, sticky="ew", padx=(8, 0), pady=2
        )

        def _do_batch():
            vuln_id = id_var.get().strip()
            if not vuln_id:
                messagebox.showwarning("警告", "请输入漏洞库ID", parent=dialog)
                return
            hosts = [
                h.strip()
                for h in hosts_text.get("1.0", tk.END).split("\n")
                if h.strip()
            ]
            if not hosts:
                messagebox.showwarning("警告", "请输入至少一个主机地址", parent=dialog)
                return
            try:
                batch = batch_create_findings(
                    self.vuln_manager,
                    vuln_id=vuln_id,
                    hosts=hosts,
                    network_zone=zone_var.get(),
                    custom_name=name_var.get().strip() or None,
                )
                self.findings.extend(batch)
                self._refresh_findings_list()
                messagebox.showinfo(
                    "完成", f"已批量录入 {len(batch)} 条漏洞记录", parent=dialog
                )
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("错误", str(e), parent=dialog)

        ttk.Button(frm, text="执行批量录入", command=_do_batch).grid(
            row=4, column=0, columnspan=2, pady=(10, 0)
        )
        ttk.Label(
            frm,
            text="提示：每行一个IP地址或URL，漏洞描述/修复建议自动从漏洞库读取",
            font=("微软雅黑", 8),
            foreground="gray",
        ).grid(row=5, column=0, columnspan=2, pady=(4, 0))

    def _emf_to_image(self, emf_data):
        if len(emf_data) < 52:
            return None
        try:
            gdi32 = ctypes.windll.gdi32
        except Exception:
            return None
        rcl = struct.unpack_from("<iiii", emf_data, 24)
        frame_w = max(rcl[2] - rcl[0], 1)
        frame_h = max(rcl[3] - rcl[1], 1)
        w_native = max(int(frame_w * 96 / 2540), 1)
        h_native = max(int(frame_h * 96 / 2540), 1)
        scale = min(1800 / w_native, 1800 / h_native, 3)
        w = max(int(w_native * scale), 1)
        h = max(int(h_native * scale), 1)

        hdc = gdi32.CreateDCW("DISPLAY", None, None, None)
        if not hdc:
            return None
        try:
            mdc = gdi32.CreateCompatibleDC(hdc)
            if not mdc:
                return None
            try:

                class BMI(ctypes.Structure):
                    _fields_ = [
                        ("biSize", ctypes.c_uint32),
                        ("biWidth", ctypes.c_int32),
                        ("biHeight", ctypes.c_int32),
                        ("biPlanes", ctypes.c_uint16),
                        ("biBitCount", ctypes.c_uint16),
                        ("biCompression", ctypes.c_uint32),
                        ("biSizeImage", ctypes.c_uint32),
                        ("biXPelsPerMeter", ctypes.c_int32),
                        ("biYPelsPerMeter", ctypes.c_int32),
                        ("biClrUsed", ctypes.c_uint32),
                        ("biClrImportant", ctypes.c_uint32),
                    ]

                bmi = BMI()
                bmi.biSize = ctypes.sizeof(BMI)
                bmi.biWidth = w
                bmi.biHeight = -h
                bmi.biPlanes = 1
                bmi.biBitCount = 32

                pBits = ctypes.c_void_p()
                hbmp = gdi32.CreateDIBSection(
                    mdc, ctypes.byref(bmi), 0, ctypes.byref(pBits), None, 0
                )
                if not hbmp:
                    return None
                try:
                    old_bmp = gdi32.SelectObject(mdc, hbmp)
                    hemf = gdi32.SetEnhMetaFileBits(len(emf_data), emf_data)
                    if hemf:
                        from ctypes import wintypes

                        gdi32.PlayEnhMetaFile(
                            mdc, hemf, ctypes.byref(wintypes.RECT(0, 0, w, h))
                        )
                        gdi32.DeleteEnhMetaFile(hemf)
                    gdi32.SelectObject(mdc, old_bmp)
                    pixel_data = ctypes.string_at(pBits, w * h * 4)
                    img = Image.frombuffer(
                        "RGBA", (w, h), pixel_data, "raw", "BGRA", 0, 1
                    )
                    return img
                finally:
                    gdi32.DeleteObject(hbmp)
            finally:
                gdi32.DeleteDC(mdc)
        finally:
            gdi32.DeleteDC(hdc)
        return None

    def _parse_html_clipboard(self, html_bytes):
        """从 Word HTML 剪贴板格式中提取文本和独立图片，保持图文顺序"""
        segments = []

        try:
            full_html = html_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return segments

        # 解析 CF_HTML 头部偏移量（偏移从整个数据的第一个字节算起）
        m_frag_start = re.search(r"StartFragment:(\d+)", full_html)
        m_frag_end = re.search(r"EndFragment:(\d+)", full_html)

        # 切掉头部 Version:...\r\n\r\n<html 之前的内容
        header_end = full_html.find("\r\n\r\n<html")
        if header_end < 0:
            header_end = full_html.find("\r\n\r\n<HTML")
        if header_end >= 0:
            full_html = full_html[header_end + 4:]
            header_len = header_end + 4
        else:
            header_len = 0

        fragment_str = full_html
        if m_frag_start and m_frag_end:
            try:
                fs = int(m_frag_start.group(1))
                fe = int(m_frag_end.group(1))
                fs_adj = fs - header_len
                fe_adj = fe - header_len
                if 0 <= fs_adj < fe_adj <= len(full_html):
                    fragment_str = full_html[fs_adj:fe_adj]
            except ValueError:
                pass

        def _img_src_to_image(src):
            try:
                if src.startswith("data:image"):
                    b64_match = re.search(r"base64,([^\s]+)", src)
                    if b64_match:
                        return Image.open(
                            io.BytesIO(base64.b64decode(b64_match.group(1)))
                        )
                elif src.startswith("file://"):
                    raw_path = src
                    for prefix in ("file:///", "file://", "file:"):
                        if raw_path.lower().startswith(prefix):
                            raw_path = raw_path[len(prefix):]
                            break
                    raw_path = raw_path.replace("/", "\\")
                    from urllib.parse import unquote

                    raw_path = unquote(raw_path)
                    if os.path.exists(raw_path):
                        return Image.open(raw_path)
            except Exception:
                pass
            return None

        img_full_pattern = re.compile(r"(<img[^>]*>)", re.IGNORECASE)
        img_src_pattern = re.compile(r'src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
        parts = img_full_pattern.split(fragment_str)

        for part in parts:
            if not part:
                continue
            if part.startswith("<img"):
                src_m = img_src_pattern.search(part)
                if src_m:
                    img = _img_src_to_image(src_m.group(1))
                    if img:
                        segments.append(img)
                        continue
                continue

            cleaned = part
            cleaned = re.sub(
                r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE
            )
            cleaned = re.sub(
                r"<script[^>]*>.*?</script>",
                "",
                cleaned,
                flags=re.DOTALL | re.IGNORECASE,
            )
            cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.DOTALL)
            cleaned = re.sub(r"<[^>]+>", "", cleaned)
            cleaned = html_mod.unescape(cleaned)
            cleaned = re.sub(r"[{}@]", "", cleaned)
            cleaned = re.sub(r"[ \t]+", " ", cleaned)
            cleaned = re.sub(r"\n\s*\n+", "\n", cleaned).strip()
            if cleaned:
                segments.append(cleaned)

        return segments

    def _read_clipboard(self):
        segments = []
        seen_hashes = set()
        fallback_images = []

        grabbed = ImageGrab.grabclipboard()
        if grabbed is not None:
            fallback_images.append(grabbed)

        try:
            win32clipboard.OpenClipboard()
            try:
                html_fmt = win32clipboard.RegisterClipboardFormat("HTML Format")
                fmt = 0
                while True:
                    fmt = win32clipboard.EnumClipboardFormats(fmt)
                    if fmt == 0:
                        break

                    if fmt == html_fmt:
                        try:
                            data = win32clipboard.GetClipboardData(fmt)
                            if data and len(data) > 100:
                                segments = self._parse_html_clipboard(data)
                        except Exception:
                            pass
                        continue

                    if fmt == 14:  # CF_ENHMETAFILE (fallback)
                        if not segments:
                            try:
                                data = win32clipboard.GetClipboardData(fmt)
                                if data and len(data) > 52:
                                    h = hash(data[:4096])
                                    if h not in seen_hashes:
                                        seen_hashes.add(h)
                                        fallback_images.append(data)
                            except Exception:
                                pass
                        continue

                    if fmt not in (8, 2):
                        continue
                    try:
                        data = win32clipboard.GetClipboardData(fmt)
                        if not data or len(data) < 4:
                            continue
                        dib_size = struct.unpack_from("<I", data, 0)[0]
                        if dib_size <= 0 or dib_size > len(data):
                            continue
                        bmp_header = struct.pack(
                            "<2sIHHI", b"BM", 14 + len(data), 0, 0, 14 + dib_size
                        )
                        full_data = bmp_header + data
                        h = hash(full_data[:4096])
                        if h in seen_hashes:
                            continue
                        seen_hashes.add(h)
                        fallback_images.append(Image.open(io.BytesIO(full_data)))
                    except Exception:
                        continue

                if not segments:
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(13):
                            text = win32clipboard.GetClipboardData(13)
                            if text:
                                segments.append(text)
                    except Exception:
                        pass
            finally:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
        except Exception:
            pass

        if not segments:
            for item in fallback_images:
                if isinstance(item, Image.Image):
                    segments.append(item)
                elif isinstance(item, bytes):
                    img = self._emf_to_image(item)
                    if img is not None:
                        segments.append(img)

        return segments

    def _paste_segments_into_widget(self, text_widget, segments):
        if not segments:
            return
        for item in segments:
            if isinstance(item, str):
                text_widget.insert(tk.INSERT, item)
            elif isinstance(item, Image.Image):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"paste_{timestamp}.png"
                filepath = os.path.join(self.screenshots_dir, filename)
                rel_path = os.path.join("screenshots", filename)

                item.save(filepath, "PNG")

                photo = ImageTk.PhotoImage(item)
                self._paste_images.append(photo)

                text_widget.insert(tk.INSERT, "\n")
                text_widget.image_create(tk.INSERT, image=photo)
                text_widget.insert(tk.INSERT, "\n")
                text_widget.insert(tk.INSERT, f"[截图: {rel_path}]\n")

    def _bind_paste_handler(self, text_widget):
        def _on_ctrl_v(event):
            try:
                segments = self._read_clipboard()
                if segments:
                    self._paste_segments_into_widget(text_widget, segments)
                    return "break"
            except Exception:
                pass
            return None

        text_widget.bind("<Control-v>", _on_ctrl_v)

    def _clear_findings(self):
        if self.findings and messagebox.askyesno("确认", "清空当前所有漏洞记录?"):
            self.findings.clear()
            self._refresh_findings_list()
            self._clear_editor()
            self.project_var.set("")

    def _load_config(self):
        path = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.project_var.set(config.get("project_name", ""))
            self.findings = config.get("findings", [])
            self._refresh_findings_list()
            messagebox.showinfo("提示", f"已加载 {len(self.findings)} 条漏洞记录")
        except Exception as e:
            messagebox.showerror("错误", f"加载失败: {e}")

    def _save_config(self):
        if not self.findings:
            messagebox.showinfo("提示", "没有可保存的漏洞记录")
            return
        path = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")],
        )
        if not path:
            return
        config = {
            "project_name": self.project_var.get().strip(),
            "findings": self.findings,
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("提示", f"配置已保存至: {path}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")

    def _generate_report(self):
        if not self.findings:
            messagebox.showwarning("警告", "请先录入至少一个漏洞")
            return

        project_name = self.project_var.get().strip() or "渗透测试报告"
        filename = filedialog.asksaveasfilename(
            title="保存报告",
            initialdir=DEFAULT_OUTPUT_DIR,
            initialfile=f"{project_name}_渗透测试报告.docx",
            defaultextension=".docx",
            filetypes=[("Word文档", "*.docx")],
        )
        if not filename:
            return

        try:
            builder = ReportBuilder(project_name=project_name)
            builder.add_summary_section(self.findings)
            builder.add_findings_section(self.findings)
            builder.save(filename)
            messagebox.showinfo("完成", f"报告已生成:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误", f"报告生成失败:\n{e}")

    def _open_library_manager(self):
        LibraryManagerDialog(self.root, self.vuln_manager, self._refresh_library_list)


# ── Library Manager Dialog ──
class LibraryManagerDialog(tk.Toplevel):
    def __init__(self, parent, vuln_manager, refresh_callback):
        super().__init__(parent)
        self.vuln_manager = vuln_manager
        self.refresh_callback = refresh_callback
        self.title("漏洞库管理")
        self.geometry("700x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        tree_frame = ttk.Frame(self, padding=(8, 8, 4, 8))
        tree_frame.grid(row=0, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("id", "name", "risk", "category")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=15,
            style="Library.Treeview",
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="名称")
        self.tree.heading("risk", text="等级")
        self.tree.heading("category", text="分类")
        self.tree.column("id", width=90)
        self.tree.column("name", width=220)
        self.tree.column("risk", width=50, anchor="center")
        self.tree.column("category", width=80, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        btn_frame = ttk.Frame(tree_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ttk.Button(btn_frame, text="新增", command=self._add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="编辑", command=self._edit).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_frame, text="删除", command=self._delete).pack(
            side=tk.LEFT, padx=2
        )

        detail_frame = ttk.LabelFrame(self, text="漏洞详情", padding=(8, 4, 8, 8))
        detail_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.detail_text = tk.Text(
            detail_frame, width=35, font=("微软雅黑", 9), wrap=tk.WORD, state="disabled"
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True)

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for v in self.vuln_manager.list_all():
            self.tree.insert(
                "",
                tk.END,
                values=(
                    v.get("id", ""),
                    v.get("name", ""),
                    v.get("risk_level", ""),
                    v.get("category", ""),
                ),
            )

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0], "values")[0]

    def _on_select(self, event):
        vuln_id = self._get_selected_id()
        if not vuln_id:
            return
        v = self.vuln_manager.get_by_id(vuln_id)
        if v:
            text = (
                f"ID: {v.get('id', '')}\n"
                f"名称: {v.get('name', '')}\n"
                f"分类: {v.get('category', '')}\n"
                f"风险等级: {v.get('risk_level', '')}\n"
                f"修复优先级: {v.get('fix_priority', '高')}\n"
                f"────────────────────────\n"
                f"描述:\n{v.get('description', '无')}\n\n"
                f"验证步骤:\n{v.get('verify_steps', '无')}\n\n"
                f"验证结果:\n{v.get('verify_result', '无')}\n\n"
                f"影响范围:\n{v.get('impact_scope', '无')}\n\n"
                f"修复建议:\n{v.get('fix_suggestion', '无')}\n\n"
                f"整改验证:\n{v.get('fix_verify', '无')}"
            )
            self.detail_text.configure(state="normal")
            self.detail_text.delete("1.0", tk.END)
            self.detail_text.insert("1.0", text)
            self.detail_text.configure(state="disabled")

    def _add(self):
        dialog = VulnEditDialog(self, self.vuln_manager)
        if dialog.result:
            self._refresh_list()
            self.refresh_callback()

    def _edit(self):
        vuln_id = self._get_selected_id()
        if not vuln_id:
            messagebox.showinfo("提示", "请先选择一个漏洞")
            return
        existing = self.vuln_manager.get_by_id(vuln_id)
        dialog = VulnEditDialog(self, self.vuln_manager, existing)
        if dialog.result:
            self._refresh_list()
            self.refresh_callback()

    def _delete(self):
        vuln_id = self._get_selected_id()
        if not vuln_id:
            return
        v = self.vuln_manager.get_by_id(vuln_id)
        if messagebox.askyesno("确认删除", f'确认删除漏洞 "{v.get("name")}"?'):
            self.vuln_manager.delete(vuln_id)
            self._refresh_list()
            self.refresh_callback()


# ── Vuln Edit Dialog ──
class VulnEditDialog(tk.Toplevel):
    def __init__(self, parent, vuln_manager, existing=None):
        super().__init__(parent)
        self.vuln_manager = vuln_manager
        self.existing = existing
        self.result = None
        self.title("编辑漏洞" if existing else "新增漏洞")
        self.geometry("550x650")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        if existing:
            self._load_existing()
        self.wait_window()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=(12, 10, 12, 10))
        frame.pack(fill=tk.BOTH, expand=True)

        labels = [
            ("漏洞ID:", "id_entry"),
            ("漏洞名称:", "name_entry"),
            ("漏洞分类:", "category_entry"),
        ]
        self.widgets = {}
        row = 0
        for label_text, attr in labels:
            ttk.Label(frame, text=label_text, font=("微软雅黑", 9, "bold")).grid(
                row=row, column=0, sticky="w", pady=3
            )
            var = tk.StringVar()
            ttk.Entry(frame, textvariable=var, font=("微软雅黑", 9), width=40).grid(
                row=row, column=1, sticky="ew", pady=3, padx=(8, 0)
            )
            self.widgets[attr] = var
            row += 1

        ttk.Label(frame, text="风险等级:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=3
        )
        risk_frame = ttk.Frame(frame)
        risk_frame.grid(row=row, column=1, sticky="w", pady=3, padx=(8, 0))
        self.widgets["risk_var"] = tk.StringVar(value="中危")
        for r in RISK_LEVELS_SHORT:
            ttk.Radiobutton(
                risk_frame, text=r, value=r, variable=self.widgets["risk_var"]
            ).pack(side=tk.LEFT, padx=2)
        row += 1

        ttk.Label(frame, text="修复优先级:", font=("微软雅黑", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=3
        )
        pri_frame = ttk.Frame(frame)
        pri_frame.grid(row=row, column=1, sticky="w", pady=3, padx=(8, 0))
        self.widgets["priority_var"] = tk.StringVar(value="高")
        for p in FIX_PRIORITIES:
            ttk.Radiobutton(
                pri_frame, text=p, value=p, variable=self.widgets["priority_var"]
            ).pack(side=tk.LEFT, padx=2)
        row += 1

        text_fields = [
            ("漏洞描述:", "description_text", 4),
            ("验证步骤:", "verify_steps_text", 4),
            ("验证结果:", "verify_result_text", 3),
            ("影响范围:", "impact_scope_text", 3),
            ("修复建议:", "fix_suggestion_text", 4),
            ("整改验证方法:", "fix_verify_text", 3),
        ]
        for label_text, attr, height in text_fields:
            ttk.Label(frame, text=label_text, font=("微软雅黑", 9, "bold")).grid(
                row=row, column=0, sticky="nw", pady=3
            )
            txt = tk.Text(
                frame, height=height, font=("微软雅黑", 9), wrap=tk.WORD, width=40
            )
            txt.grid(row=row, column=1, sticky="ew", pady=3, padx=(8, 0))
            self.widgets[attr] = txt
            row += 1

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(btn_frame, text="保存", command=self._save).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(
            side=tk.RIGHT, padx=4
        )

    def _load_existing(self):
        e = self.existing
        self.widgets["id_entry"].set(e.get("id", ""))
        if self.existing:
            self.widgets["id_entry"].configure(state="readonly")
        self.widgets["name_entry"].set(e.get("name", ""))
        self.widgets["category_entry"].set(e.get("category", ""))
        self.widgets["risk_var"].set(e.get("risk_level", "中危"))
        self.widgets["priority_var"].set(e.get("fix_priority", "高"))
        for field, attr in [
            ("description", "description_text"),
            ("verify_steps", "verify_steps_text"),
            ("verify_result", "verify_result_text"),
            ("impact_scope", "impact_scope_text"),
            ("fix_suggestion", "fix_suggestion_text"),
            ("fix_verify", "fix_verify_text"),
        ]:
            self.widgets[attr].insert("1.0", e.get(field, ""))

    def _save(self):
        vuln_id = self.widgets["id_entry"].get().strip()
        name = self.widgets["name_entry"].get().strip()
        if not vuln_id or not name:
            messagebox.showwarning("警告", "ID和名称不能为空")
            return

        data = {
            "id": vuln_id,
            "name": name,
            "category": self.widgets["category_entry"].get().strip(),
            "risk_level": self.widgets["risk_var"].get(),
            "fix_priority": self.widgets["priority_var"].get(),
        }
        for field, attr in [
            ("description", "description_text"),
            ("verify_steps", "verify_steps_text"),
            ("verify_result", "verify_result_text"),
            ("impact_scope", "impact_scope_text"),
            ("fix_suggestion", "fix_suggestion_text"),
            ("fix_verify", "fix_verify_text"),
        ]:
            data[field] = self.widgets[attr].get("1.0", tk.END).strip()

        try:
            if self.existing:
                self.vuln_manager.update(vuln_id, data)
            else:
                self.vuln_manager.add(data)
            self.result = data
            self.destroy()
        except ValueError as e:
            messagebox.showerror("错误", str(e))


def main():
    root = tk.Tk()
    PentestReportApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
