#!/usr/bin/env python3
"""
部署验证脚本
用于验证Docker Compose部署是否正常运行
"""

import asyncio
import httpx
import time
import sys
from typing import Dict, Any

class DeploymentVerifier:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.timeout = 30
        self.checks = {}

    async def check_health(self) -> Dict[str, Any]:
        """检查基础健康状态"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "pass",
                        "service": data.get("service"),
                        "version": data.get("version"),
                        "timestamp": data.get("timestamp")
                    }
                else:
                    return {"status": "fail", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "fail", "error": str(e)}

    async def check_detailed_health(self) -> Dict[str, Any]:
        """检查详细健康状态"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health/detailed")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "pass",
                        "overall": data.get("status"),
                        "components": data.get("components", {}),
                        "uptime": data.get("uptime")
                    }
                else:
                    return {"status": "fail", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "fail", "error": str(e)}

    async def check_readiness(self) -> Dict[str, Any]:
        """检查服务就绪状态"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health/ready")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "pass",
                        "ready": data.get("ready"),
                        "checks": data.get("checks", {})
                    }
                else:
                    return {"status": "fail", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "fail", "error": str(e)}

    async def check_liveness(self) -> Dict[str, Any]:
        """检查服务存活状态"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health/live")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "pass",
                        "alive": data.get("alive"),
                        "timestamp": data.get("timestamp")
                    }
                else:
                    return {"status": "fail", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "fail", "error": str(e)}

    async def check_metrics(self) -> Dict[str, Any]:
        """检查指标端点"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/metrics")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "pass",
                        "system_metrics": data.get("system", {}),
                        "process_metrics": data.get("process", {})
                    }
                else:
                    return {"status": "fail", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "fail", "error": str(e)}

    async def check_api_docs(self) -> Dict[str, Any]:
        """检查API文档"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/docs")
                if response.status_code == 200:
                    return {"status": "pass", "content_type": response.headers.get("content-type")}
                else:
                    return {"status": "fail", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "fail", "error": str(e)}

    async def wait_for_service(self, max_wait: int = 120) -> bool:
        """等待服务启动"""
        print("等待服务启动...")
        for i in range(max_wait):
            try:
                result = await self.check_health()
                if result["status"] == "pass":
                    print(f"✓ 服务启动成功 (耗时: {i+1}s)")
                    return True
            except Exception:
                pass

            if i % 10 == 0:
                print(f"等待中... ({i+1}s)")
            await asyncio.sleep(1)

        print("✗ 服务启动超时")
        return False

    async def run_all_checks(self) -> Dict[str, Any]:
        """运行所有检查"""
        print("开始部署验证...")

        # 等待服务启动
        if not await self.wait_for_service():
            return {"overall": "fail", "error": "服务启动超时"}

        print("\n运行详细检查...")

        # 运行所有检查
        checks = {
            "health": await self.check_health(),
            "detailed_health": await self.check_detailed_health(),
            "readiness": await self.check_readiness(),
            "liveness": await self.check_liveness(),
            "metrics": await self.check_metrics(),
            "api_docs": await self.check_api_docs()
        }

        # 分析结果
        passed = sum(1 for check in checks.values() if check.get("status") == "pass")
        total = len(checks)

        print(f"\n检查结果: {passed}/{total} 通过")

        for name, result in checks.items():
            status_icon = "✓" if result.get("status") == "pass" else "✗"
            print(f"{status_icon} {name}: {result.get('status', 'unknown')}")
            if result.get("status") == "fail":
                print(f"  错误: {result.get('error', 'unknown')}")

        return {
            "overall": "pass" if passed == total else "fail",
            "passed": passed,
            "total": total,
            "checks": checks
        }

async def main():
    """主函数"""
    verifier = DeploymentVerifier()
    result = await verifier.run_all_checks()

    print(f"\n部署验证结果: {result['overall']}")

    if result['overall'] == 'pass':
        print("✓ 所有检查通过，部署成功！")
        sys.exit(0)
    else:
        print("✗ 部署验证失败")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())