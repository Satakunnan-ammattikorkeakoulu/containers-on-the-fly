#!/usr/bin/env python3

"""
Settings Application Script for Containers on the Fly

This script reads the user_config/settings file and applies the configuration
to template files, generating the final configuration files needed by the application.

Usage:
    python3 scripts/apply_settings.py
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path


class SettingsApplier:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.settings_file = self.base_dir / "user_config" / "settings"
        self.templates_dir = self.base_dir / "user_config" / "templates"
        self.output_dir = self.base_dir / "user_config"
        self.settings = {}
        
    def load_settings(self):
        """Load settings from the settings file."""
        if not self.settings_file.exists():
            print(f"Error: Settings file not found at {self.settings_file}")
            print("Please copy user_config/settings_example to user_config/settings and configure it.")
            sys.exit(1)
            
        print(f"Loading settings from {self.settings_file}")
        
        # Read the bash settings file
        with open(self.settings_file, 'r') as f:
            content = f.read()
            
        # Extract variable assignments
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                # Handle variable assignments
                if line.startswith('export '):
                    line = line[7:]  # Remove 'export '
                    
                # Split on first '=' only
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes from value
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                    
                self.settings[key] = value
                
        # Process derived settings
        self._process_derived_settings()
        self._process_caddy_settings()
        print(f"Loaded {len(self.settings)} settings")
        
    def _process_derived_settings(self):
        """Process derived settings that depend on other settings."""
        # Build database URI
        db_uri = f"mysql+pymysql://{self.settings.get('MARIADB_DB_USER', '')}:{self.settings.get('MARIADB_DB_USER_PASSWORD', '')}@{self.settings.get('MARIADB_SERVER_ADDRESS', 'localhost')}/{self.settings.get('MARIADB_DB_NAME', '')}"
        self.settings['DATABASE_URI'] = db_uri
        
        # Handle backend additional port
        backend_port = self.settings.get('BACKEND_ADDITIONAL_PORT', '')
        if backend_port:
            self.settings['BACKEND_ADDITIONAL_PORT'] = f":{backend_port}"
        else:
            self.settings['BACKEND_ADDITIONAL_PORT'] = ""
            
        # Convert boolean strings to proper JSON boolean values
        bool_settings = [
            'USE_WHITELIST', 'DATABASE_DEBUG', 'ADD_TEST_DATA', 
            'ENABLE_EMAIL_NOTIFICATIONS', 'ENABLE_AUTO_HTTPS'
        ]
        
        for setting in bool_settings:
            if setting in self.settings:
                value = self.settings[setting].lower()
                if value in ['true', '1', 'yes', 'on']:
                    self.settings[setting] = 'true'  # JSON boolean
                else:
                    self.settings[setting] = 'false'  # JSON boolean
                    
        # Validate numeric settings (keep as strings for template replacement)
        numeric_settings = [
            'RESERVATION_MIN_DURATION', 'RESERVATION_MAX_DURATION',
            'SESSION_TIMEOUT_MINUTES', 'BACKEND_PORT', 'FRONTEND_PORT',
            'SMTP_PORT', 'DOCKER_REGISTRY_PORT', 
            'DOCKER_RESERVATION_PORT_RANGE_START', 'DOCKER_RESERVATION_PORT_RANGE_END'
        ]
        
        for setting in numeric_settings:
            if setting in self.settings:
                try:
                    # Validate it's numeric but keep as string for template replacement
                    int(self.settings[setting])
                except ValueError:
                    print(f"Warning: {setting} should be numeric, got: {self.settings[setting]}")
                    
    def _process_caddy_settings(self):
        """Process Caddy-specific settings based on HTTPS configuration."""
        enable_https = self.settings.get('ENABLE_AUTO_HTTPS', 'false').lower() == 'true'
        domain = self.settings.get('SERVER_DOMAIN', 'localhost')
        
        if enable_https:
            # HTTPS mode - automatic certificates
            self.settings['CADDY_SITE_BLOCK'] = domain
            self.settings['CADDY_SECURITY_HEADERS'] = " (HTTPS mode)"
            self.settings['CADDY_HSTS_HEADER'] = "\n\t\t# Enable HSTS for HTTPS\n\t\tStrict-Transport-Security max-age=31536000;"
            print(f"Caddy mode: HTTPS enabled for domain '{domain}' (automatic Let's Encrypt)")
        else:
            # HTTP mode - no automatic certificates
            self.settings['CADDY_SITE_BLOCK'] = f"http://{domain}"
            self.settings['CADDY_SECURITY_HEADERS'] = " (HTTP mode)"
            self.settings['CADDY_HSTS_HEADER'] = ""
            print(f"Caddy mode: HTTP only for '{domain}' (no SSL certificates)")
                    
    def apply_templates(self):
        """Apply settings to all template files."""
        if not self.templates_dir.exists():
            print(f"Error: Templates directory not found at {self.templates_dir}")
            sys.exit(1)
            
        # Define where each template should output its final file
        template_mappings = {
            'backend_settings.json': self.base_dir / "webapp" / "backend" / "settings.json",
            'frontend_settings.js': self.base_dir / "webapp" / "frontend" / "src" / "AppSettings.js",
            'Caddyfile': self.output_dir / "Caddyfile"  # Only Caddyfile stays in user_config
        }
        
        for template_file, output_path in template_mappings.items():
            template_path = self.templates_dir / template_file
            
            if template_path.exists():
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._apply_template(template_path, output_path)
            else:
                print(f"Warning: Template file not found: {template_path}")
                
    def _apply_template(self, template_path, output_path):
        """Apply settings to a single template file."""
        print(f"Processing template: {template_path} -> {output_path}")
        
        with open(template_path, 'r') as f:
            content = f.read()
            
        # Replace all placeholders
        for key, value in self.settings.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))
            
        # Check for unreplaced placeholders
        unreplaced = re.findall(r'\{\{([^}]+)\}\}', content)
        if unreplaced:
            print(f"Warning: Unreplaced placeholders in {template_path}: {unreplaced}")
            
        # Write output file
        try:
            with open(output_path, 'w') as f:
                f.write(content)
            print(f"Generated: {output_path}")
            
            # If running as root, fix ownership to the original user
            self._fix_file_ownership(output_path)
            
        except PermissionError:
            print(f"Warning: Permission denied writing to {output_path}")
            print(f"This file may be owned by root. You can fix this by running:")
            print(f"  sudo rm {output_path}")
            print(f"  Then re-run this command.")
            # Don't fail the entire process, just skip this file
            return
        
    def _fix_file_ownership(self, file_path):
        """Fix file ownership when running as root to match the original user."""
        # Only try to fix ownership if running as root
        if os.geteuid() != 0:
            return
            
        # Get the original user from SUDO_USER environment variable
        sudo_user = os.environ.get('SUDO_USER')
        if not sudo_user:
            return
            
        try:
            # Get the UID and GID of the original user
            import pwd
            import grp
            user_info = pwd.getpwnam(sudo_user)
            uid = user_info.pw_uid
            gid = user_info.pw_gid
            
            # Change ownership
            os.chown(file_path, uid, gid)
            print(f"Fixed ownership of {file_path} to {sudo_user}")
            
        except (KeyError, OSError) as e:
            print(f"Warning: Could not fix ownership of {file_path}: {e}")
    
    def copy_to_webapp(self):
        """This method is no longer needed since files are written directly to their final locations."""
        pass
            
    def run(self):
        """Run the complete settings application process."""
        print("=== Containers on the Fly - Settings Application ===")
        
        try:
            self.load_settings()
            self.apply_templates()
            print("\n✅ Settings applied successfully!")
            print(f"Generated files:")
            print(f"  - Backend settings: webapp/backend/settings.json")
            print(f"  - Frontend settings: webapp/frontend/src/AppSettings.js")  
            print(f"  - Caddy config: user_config/Caddyfile")
            
        except Exception as e:
            print(f"\n❌ Error applying settings: {e}")
            sys.exit(1)


if __name__ == "__main__":
    applier = SettingsApplier()
    applier.run() 