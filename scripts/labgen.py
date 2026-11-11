#!/usr/bin/env python3
"""labgen.py：生成验证用实验环境的 IaC（Terraform + Ansible）与说明。

三条硬约束（02 第 10.6 节）：
1. 初始口令随机化：由 Terraform random_password 在 apply 时生成，不写入任何生成文件，不存在固定口令；
2. 入站仅允许管理网段：--mgmt-cidr 必填，拒绝 0.0.0.0/0 与任何 /0；Terraform 变量也做同样校验；
3. README 首行写明「仅用于验证，不得用于生产」。
镜像版本、区域等易变事实不写死，作为变量由使用者按核查锚点填写。
退出码：0 成功；2 参数或文件错误。
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as R  # noqa: E402

PROVIDERS = {"azure"}
README_FIRST_LINE = "仅用于验证，不得用于生产。"
TOPOLOGY = {  # 角色名: 说明
    "sccm": [("dc01", "域控（实验用单域）"), ("site01", "配置管理器站点服务器（与域控分离）"), ("client01", "铺装对象终端")],
    "admerge": [("srcdc01", "源林域控"), ("tgtdc01", "目标林域控"), ("member01", "迁移对象成员服务器")],
    "entraconnect": [("dc01", "域控"), ("sync01", "同步服务器（不得与域控同机）")],
}


def validate_cidr(text: str) -> str:
    try:
        net = ipaddress.ip_network(text, strict=False)
    except ValueError as exc:
        raise R.ConfigError(f"--mgmt-cidr 格式错误：{text}") from exc
    if net.prefixlen == 0:
        raise R.ConfigError("--mgmt-cidr 不得为 0.0.0.0/0 或任何 /0 网段：入站只允许管理网段")
    return str(net)


def variables_tf() -> str:
    return '''variable "location" {
  description = "部署区域（由使用者填写）"
  type        = string
}

variable "prefix" {
  description = "资源名前缀"
  type        = string
}

variable "mgmt_cidr" {
  description = "唯一允许入站的管理网段"
  type        = string
  validation {
    condition = (
      can(cidrhost(var.mgmt_cidr, 0)) &&
      length(split("/", var.mgmt_cidr)) == 2 &&
      can(tonumber(split("/", var.mgmt_cidr)[1])) &&
      try(tonumber(split("/", var.mgmt_cidr)[1]), 0) > 0
    )
    error_message = "mgmt_cidr 必须是前缀长度大于 0 的合法 CIDR（禁止 0.0.0.0/0、*、Internet 等全网来源）。"
  }
}

variable "vnet_cidr" {
  description = "实验网络地址段（由使用者填写，勿与客户网络重叠）"
  type        = string
}

variable "vm_size" {
  description = "虚拟机规格（由使用者填写）"
  type        = string
}

variable "windows_image" {
  description = "Windows Server 镜像。版本按核查锚点核实后填写，本工具不写死版本"
  type = object({
    publisher = string
    offer     = string
    sku       = string
    version   = string
  })
}

variable "admin_username" {
  description = "初始管理员用户名（口令由 random_password 随机生成）"
  type        = string
}
'''


def main_tf(roles: list[tuple[str, str]]) -> str:
    blocks = ['''terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    random  = { source = "hashicorp/random" }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "lab" {
  name     = "${var.prefix}-rg"
  location = var.location
  tags     = { purpose = "verification-only" }
}

resource "azurerm_virtual_network" "lab" {
  name                = "${var.prefix}-vnet"
  address_space       = [var.vnet_cidr]
  location            = azurerm_resource_group.lab.location
  resource_group_name = azurerm_resource_group.lab.name
}

resource "azurerm_subnet" "lab" {
  name                 = "${var.prefix}-subnet"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.lab.name
  address_prefixes     = [cidrsubnet(var.vnet_cidr, 8, 1)]
}

resource "azurerm_network_security_group" "lab" {
  name                = "${var.prefix}-nsg"
  location            = azurerm_resource_group.lab.location
  resource_group_name = azurerm_resource_group.lab.name

  security_rule {
    name                       = "allow-mgmt-only"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["3389", "5986"]
    source_address_prefix      = var.mgmt_cidr
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "lab" {
  subnet_id                 = azurerm_subnet.lab.id
  network_security_group_id = azurerm_network_security_group.lab.id
}
''']
    for role, desc in roles:
        blocks.append(f'''
# {desc}
resource "random_password" "{role}" {{
  length           = 24
  special          = true
  override_special = "!@#%*-_=+"
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
}}

resource "azurerm_network_interface" "{role}" {{
  name                = "${{var.prefix}}-{role}-nic"
  location            = azurerm_resource_group.lab.location
  resource_group_name = azurerm_resource_group.lab.name
  ip_configuration {{
    name                          = "internal"
    subnet_id                     = azurerm_subnet.lab.id
    private_ip_address_allocation = "Dynamic"
  }}
}}

resource "azurerm_windows_virtual_machine" "{role}" {{
  name                  = "${{var.prefix}}-{role}"
  location              = azurerm_resource_group.lab.location
  resource_group_name   = azurerm_resource_group.lab.name
  size                  = var.vm_size
  admin_username        = var.admin_username
  admin_password        = random_password.{role}.result
  network_interface_ids = [azurerm_network_interface.{role}.id]
  os_disk {{
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }}
  source_image_reference {{
    publisher = var.windows_image.publisher
    offer     = var.windows_image.offer
    sku       = var.windows_image.sku
    version   = var.windows_image.version
  }}
  tags = {{ role = "{role}", purpose = "verification-only" }}
}}
''')
    return "".join(blocks)


def outputs_tf(roles) -> str:
    out = []
    for role, _ in roles:
        out.append(f'''output "{role}_private_ip" {{
  value = azurerm_network_interface.{role}.private_ip_address
}}

output "{role}_admin_password" {{
  value     = random_password.{role}.result
  sensitive = true
}}
''')
    return "\n".join(out)


def ansible_files(ptype: str, roles) -> dict[str, str]:
    hosts = "\n".join(f"    {r}:\n      ansible_host: \"{{{{ lookup('env', '{r.upper()}_IP') }}}}\"" for r, _ in roles)
    inventory = f"""# 主机地址由 terraform output 注入环境变量，不在此写死
all:
  vars:
    ansible_connection: winrm
    ansible_port: 5986
    ansible_winrm_transport: ntlm
    ansible_winrm_server_cert_validation: validate
    ansible_user: "{{{{ lookup('env', 'LAB_ADMIN_USER') }}}}"
    ansible_password: "{{{{ lookup('env', 'LAB_ADMIN_PASSWORD') }}}}"
  hosts:
{hosts}
"""
    first = roles[0][0]
    playbook = f"""# 实验环境初始化（{R.TYPE_META[ptype]['label']}）。口令经环境变量传入，不落盘。
- name: 基础设置（全部主机）
  hosts: all
  gather_facts: false
  tasks:
    - name: 确认 WinRM 可达
      ansible.windows.win_ping:

- name: 域控角色安装（{first}）
  hosts: {first}
  gather_facts: false
  tasks:
    - name: 安装目录服务角色
      ansible.windows.win_feature:
        name: AD-Domain-Services
        include_management_tools: true
        state: present
"""
    return {"ansible/inventory.yml": inventory, "ansible/playbook.yml": playbook}


def readme(ptype: str, provider: str, mgmt: str, roles) -> str:
    role_rows = "\n".join(f"| {r} | {d} |" for r, d in roles)
    return f"""{README_FIRST_LINE}

# 实验环境：{R.TYPE_META[ptype]['label']}（{provider}）

本目录由 ringi-kit `labgen.py` 生成，用于在客户环境之外复现 Gate 检查与回退演练。

## 主机构成

| 角色 | 说明 |
|---|---|
{role_rows}

## 安全约束

- 初始口令由 Terraform `random_password` 在 apply 时随机生成，只保存在 Terraform 状态中（输出标记为 sensitive）；本目录任何文件都不含口令。
- 入站只允许管理网段 `{mgmt}` 访问 3389 / 5986，其余入站全部拒绝；变量校验拒绝任何 /0 网段。
- 镜像版本、区域、规格不写死，按核查锚点（AN-03、AN-06）的核实结果填写 `terraform.tfvars`。
- Terraform 状态文件含口令，须按 `credentials/` 规范保管，不得提交到仓库。

## 使用步骤

1. 复制 `terraform/terraform.tfvars.example` 为 `terraform.tfvars` 并填写全部变量。
2. `terraform init` → `terraform plan` → 确认计划中无 0.0.0.0/0 入站后 `terraform apply`。
3. 以 `terraform output -json` 取得各主机地址与口令，设置环境变量后执行 `ansible-playbook -i ansible/inventory.yml ansible/playbook.yml`。
4. 验证完毕后 `terraform destroy`，并删除本地状态文件。
"""


def tfvars_example(mgmt: str) -> str:
    return f'''# 填写后另存为 terraform.tfvars（不含任何口令）
location       = "<按需求填写区域>"
prefix         = "ringi-lab"
mgmt_cidr      = "{mgmt}"
vnet_cidr      = "<实验网络地址段，勿与客户网络重叠>"
vm_size        = "<虚拟机规格>"
admin_username = "<初始管理员用户名>"
windows_image = {{
  publisher = "<按核查锚点填写>"
  offer     = "<按核查锚点填写>"
  sku       = "<按核查锚点填写>"
  version   = "<按核查锚点填写>"
}}
'''


def generate(ptype: str, provider: str, mgmt: str) -> dict[str, str]:
    roles = TOPOLOGY[ptype]
    files = {
        "README.md": readme(ptype, provider, mgmt, roles),
        "terraform/main.tf": main_tf(roles),
        "terraform/variables.tf": variables_tf(),
        "terraform/outputs.tf": outputs_tf(roles),
        "terraform/terraform.tfvars.example": tfvars_example(mgmt),
        ".gitignore": "terraform/*.tfstate*\nterraform/.terraform/\nterraform/terraform.tfvars\n",
    }
    files.update(ansible_files(ptype, roles))
    return files


def main(argv=None) -> int:
    R.utf8_stdout()
    ap = argparse.ArgumentParser(description="生成验证用实验环境（Terraform + Ansible）")
    ap.add_argument("--type", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--provider", default="azure")
    ap.add_argument("--mgmt-cidr", required=True, help="唯一允许入站的管理网段，禁止 /0")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.type not in TOPOLOGY:
            raise R.ConfigError(f"不支持的项目类型：{args.type}。仅支持 sccm / admerge / entraconnect")
        if args.provider not in PROVIDERS:
            raise R.ConfigError(f"不支持的云平台：{args.provider}。当前仅支持 azure")
        mgmt = validate_cidr(args.mgmt_cidr)
        files = generate(args.type, args.provider, mgmt)
        out = Path(args.out).resolve()
        for rel, text in files.items():
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
    except R.ConfigError as exc:
        R.emit("labgen", {"status": "error", "exit_code": R.EXIT_ARG, "message": str(exc)}, args.json)
        return R.EXIT_ARG
    R.emit("labgen", {"status": "ok", "exit_code": 0, "message": f"已生成实验环境到 {args.out}",
                      "files": sorted(files)}, args.json)
    return R.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
