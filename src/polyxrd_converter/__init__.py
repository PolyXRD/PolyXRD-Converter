"""
PolyXRD Converter —— XRD 谱图格式转换器
========================================
从 PolyXRD 中独立剥离出来的「谱图格式互转」小工具。

- 读: 支持 xy / txt / dat / csv / mdi / xrdml / xml / brml / json
      以及多种厂商二进制 RAW (自动识别, 见 ``raw_formats``)
- 写: xy / txt / dat / csv / mdi / raw / xrdml / json
- 用: ``convert_file(src, dst, fmt)`` / ``load_pattern(path)``, 或直接跑 GUI

与 PolyXRD 主体零耦合: 只依赖 numpy 与 PySide6。

v1.1.0: 岛津 .RAW 解析精度升级 —— 截断文件防护 (钳到可用点数 + truncated
标记 + 截断时角度轴强制转人工), 与 PolyXRD 主体 ``DataLoader._load_shimadzu_raw``
全量对拍验证 (强度逐点全等)。
v1.2.0: 修复 writers._fmt_pair 两列粘连 (P1, 高强度/大整数样本不再塌缩成单列);
新增 θ 单轴摇摆扫描 GUI 提示 (P2); 验证扩到 252 断言 + 冒烟 40。
v1.3.0: 新增 GSAS-II 系 5 类文本格式读取器 (gsas/fp_dat/ras/xye/chi) —— 格式
知识参考 GSAS-II 开源 importer 并按其许可注明来源, 与 GSAS-II 本体 oracle
对拍 10 种格式逐点全等; 验证扩到 311 断言 + 冒烟 40。
"""

__version__ = "1.3.0"
__author__ = "PolyXRD Team"
__app_name__ = "PolyXRD Converter"

__all__ = ["__version__", "__app_name__"]
