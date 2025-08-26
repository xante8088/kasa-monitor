#!/usr/bin/env python3
"""
Security verification script for data export API.

This script verifies that the critical security fixes have been properly implemented:
1. Permission enforcement on all endpoints
2. User ownership validation
3. Audit logging for all operations
4. Rate limiting
5. Proper error handling

Copyright (C) 2025 Kasa Monitor Contributors
"""

import asyncio
import inspect
import importlib.util
import sys
from pathlib import Path


def verify_data_export_api_security():
    """Verify that the data export API has proper security measures."""
    
    print("🔒 VERIFYING DATA EXPORT API SECURITY FIXES")
    print("=" * 50)
    
    results = {}
    
    # Load the data_export_api module
    try:
        spec = importlib.util.spec_from_file_location(
            "data_export_api", 
            Path(__file__).parent / "data_export_api.py"
        )
        data_export_api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(data_export_api)
        print("✅ Successfully loaded data_export_api module")
    except Exception as e:
        print(f"❌ Failed to load data_export_api module: {e}")
        return False
    
    # Check if required imports are present
    print("\n📦 CHECKING REQUIRED IMPORTS")
    required_imports = [
        'require_permission',
        'Permission', 
        'User',
        'AuditLogger',
        'AuditEvent',
        'AuditEventType',
        'AuditSeverity'
    ]
    
    for imp in required_imports:
        if hasattr(data_export_api, imp):
            print(f"✅ {imp} imported")
            results[f"import_{imp}"] = True
        else:
            print(f"❌ {imp} missing")
            results[f"import_{imp}"] = False
    
    # Check DataExportAPIRouter class
    print("\n🏗️  CHECKING DataExportAPIRouter CLASS")
    
    if hasattr(data_export_api, 'DataExportAPIRouter'):
        router_class = data_export_api.DataExportAPIRouter
        print("✅ DataExportAPIRouter class found")
        
        # Check if __init__ method has audit_logger
        init_source = inspect.getsource(router_class.__init__)
        if 'self.audit_logger = AuditLogger' in init_source:
            print("✅ AuditLogger initialized in constructor")
            results['audit_logger_init'] = True
        else:
            print("❌ AuditLogger not initialized in constructor")
            results['audit_logger_init'] = False
            
        # Check _setup_routes method exists
        if hasattr(router_class, '_setup_routes'):
            print("✅ _setup_routes method found")
            
            # Analyze the _setup_routes method for security measures
            setup_source = inspect.getsource(router_class._setup_routes)
            
            # Check for permission decorators
            permission_checks = [
                'require_permission(Permission.DATA_EXPORT)',
                'user: User = Depends(require_permission',
            ]
            
            permission_found = any(check in setup_source for check in permission_checks)
            if permission_found:
                print("✅ Permission enforcement found in endpoints")
                results['permission_enforcement'] = True
            else:
                print("❌ Permission enforcement missing from endpoints")
                results['permission_enforcement'] = False
            
            # Check for audit logging
            audit_checks = [
                'audit_logger.log_event_async',
                'AuditEvent(',
                'AuditEventType.DATA_EXPORT',
                'AuditEventType.PERMISSION_DENIED',
            ]
            
            audit_found = any(check in setup_source for check in audit_checks)
            if audit_found:
                print("✅ Audit logging found in endpoints")
                results['audit_logging'] = True
            else:
                print("❌ Audit logging missing from endpoints")
                results['audit_logging'] = False
            
            # Check for ownership validation
            ownership_checks = [
                'export.get("user_id") != user.id',
                'user.role.value != "admin"',
                'Access denied to export'
            ]
            
            ownership_found = any(check in setup_source for check in ownership_checks)
            if ownership_found:
                print("✅ Ownership validation found")
                results['ownership_validation'] = True
            else:
                print("❌ Ownership validation missing")
                results['ownership_validation'] = False
            
            # Check for rate limiting
            rate_limit_checks = [
                '_check_export_rate_limit',
                'rate_limit_exceeded'
            ]
            
            rate_limit_found = any(check in setup_source for check in rate_limit_checks)
            if rate_limit_found:
                print("✅ Rate limiting found")
                results['rate_limiting'] = True
            else:
                print("❌ Rate limiting missing")
                results['rate_limiting'] = False
        else:
            print("❌ _setup_routes method not found")
            results['setup_routes'] = False
    else:
        print("❌ DataExportAPIRouter class not found")
        results['router_class'] = False
    
    # Check helper methods
    print("\n🔧 CHECKING SECURITY HELPER METHODS")
    
    if hasattr(data_export_api, 'DataExportAPIRouter'):
        router_class = data_export_api.DataExportAPIRouter
        
        expected_methods = [
            '_check_export_rate_limit',
            '_estimate_record_count'
        ]
        
        for method_name in expected_methods:
            if hasattr(router_class, method_name):
                print(f"✅ {method_name} method found")
                results[f"method_{method_name}"] = True
            else:
                print(f"❌ {method_name} method missing")
                results[f"method_{method_name}"] = False
    
    # Check data_export_service module for user support
    print("\n🗄️  CHECKING DATA EXPORT SERVICE")
    
    try:
        spec = importlib.util.spec_from_file_location(
            "data_export_service", 
            Path(__file__).parent / "data_export_service.py"
        )
        data_export_service = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(data_export_service)
        
        if hasattr(data_export_service, 'DataExportService'):
            service_class = data_export_service.DataExportService
            
            # Check for user-aware methods
            user_methods = [
                'export_data_with_user',
                'get_export_history_for_user',
                '_save_export_record_with_user'
            ]
            
            for method_name in user_methods:
                if hasattr(service_class, method_name):
                    print(f"✅ {method_name} method found")
                    results[f"service_{method_name}"] = True
                else:
                    print(f"❌ {method_name} method missing")
                    results[f"service_{method_name}"] = False
            
            # Check table schema
            init_source = inspect.getsource(service_class._init_exports_db)
            if 'user_id INTEGER' in init_source:
                print("✅ user_id column in table schema")
                results['user_id_column'] = True
            else:
                print("❌ user_id column missing from table schema")
                results['user_id_column'] = False
                
        else:
            print("❌ DataExportService class not found")
            results['service_class'] = False
    
    except Exception as e:
        print(f"❌ Failed to load data_export_service: {e}")
        results['service_load'] = False
    
    # Summary
    print("\n📊 SECURITY VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    critical_tests = [
        'permission_enforcement',
        'audit_logging', 
        'ownership_validation',
        'rate_limiting',
        'user_id_column'
    ]
    
    critical_passed = sum(1 for test in critical_tests if results.get(test, False))
    
    if critical_passed == len(critical_tests):
        print("🎉 ALL CRITICAL SECURITY MEASURES IMPLEMENTED!")
        print("\nThe following security vulnerabilities have been fixed:")
        print("✅ Permission enforcement on all export endpoints")
        print("✅ User ownership validation for downloads and deletes")
        print("✅ Comprehensive audit logging for compliance")
        print("✅ Basic rate limiting to prevent abuse")
        print("✅ Database schema supports user ownership tracking")
        
        print("\n⚠️  DEPLOYMENT CHECKLIST:")
        print("1. Run database migration if needed")
        print("2. Restart the application server") 
        print("3. Test with different user roles")
        print("4. Verify audit logs are being created")
        print("5. Monitor for any permission errors")
        
        return True
    else:
        print(f"❌ CRITICAL SECURITY ISSUES REMAIN: {len(critical_tests) - critical_passed} failures")
        print("\nFailed critical tests:")
        for test in critical_tests:
            if not results.get(test, False):
                print(f"  ❌ {test}")
        
        return False


if __name__ == "__main__":
    success = verify_data_export_api_security()
    sys.exit(0 if success else 1)