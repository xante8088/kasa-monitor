"""SSL Certificate Management API endpoints.

Copyright (C) 2025 Kasa Monitor Contributors

This file is part of Kasa Monitor.

Kasa Monitor is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Kasa Monitor is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Kasa Monitor. If not, see <https://www.gnu.org/licenses/>.
"""

import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Response, Depends
from pydantic import BaseModel, Field

from auth import verify_token
from ssl_manager import SSLCertificateManager

router = APIRouter(prefix="/api/ssl", tags=["SSL Certificate Management"])

# Initialize SSL manager
ssl_manager = SSLCertificateManager()


class CSRRequest(BaseModel):
    """Request model for CSR generation."""
    country: str = Field(..., min_length=2, max_length=2, description="Two-letter country code (e.g., US)")
    state: str = Field(..., min_length=1, max_length=128, description="State or province")
    city: str = Field(..., min_length=1, max_length=64, description="City or locality")
    organization: str = Field(..., min_length=1, max_length=64, description="Organization name")
    organizational_unit: str = Field("", max_length=64, description="Organizational unit (optional)")
    common_name: str = Field(..., min_length=1, max_length=64, description="Common name (domain)")
    email: str = Field(..., description="Email address")
    san_domains: Optional[List[str]] = Field(default=None, description="Subject Alternative Names (optional)")
    key_size: int = Field(default=2048, ge=2048, le=4096, description="RSA key size (2048-4096)")


class FileDeleteRequest(BaseModel):
    """Request model for file deletion."""
    filename: str = Field(..., min_length=1, description="Name of file to delete")
    confirmation: str = Field(..., description="Confirmation text (must be 'delete')")


class DownloadRequest(BaseModel):
    """Request model for file download."""
    filenames: List[str] = Field(..., min_items=1, description="List of filenames to download")


@router.post("/generate-csr")
async def generate_csr(request: CSRRequest, user_info: dict = Depends(verify_token)):
    """Generate a new CSR and private key."""
    try:
        # Clean up old temp files
        ssl_manager.cleanup_temp_files()
        
        # Generate CSR and private key
        key_path, csr_path = ssl_manager.generate_csr_and_key(
            country=request.country.upper(),
            state=request.state,
            city=request.city,
            organization=request.organization,
            organizational_unit=request.organizational_unit,
            common_name=request.common_name,
            email=request.email,
            san_domains=request.san_domains,
            key_size=request.key_size
        )
        
        return {
            "success": True,
            "message": "CSR and private key generated successfully",
            "key_file": os.path.basename(key_path),
            "csr_file": os.path.basename(csr_path),
            "key_path": key_path,
            "csr_path": csr_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate CSR: {str(e)}")


@router.get("/files")
async def list_ssl_files(user_info: dict = Depends(verify_token)):
    """List all SSL files in the directory."""
    try:
        files = ssl_manager.list_ssl_files()
        return {
            "success": True,
            "files": files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/download/{filename}")
async def download_file(filename: str, user_info: dict = Depends(verify_token)):
    """Download a single SSL file."""
    try:
        # Security validation
        if not filename or ".." in filename or "/" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        content = ssl_manager.get_file_content(filename)
        
        # Determine content type based on file extension
        content_type = "application/octet-stream"
        if filename.endswith(('.csr', '.crt', '.pem', '.key')):
            content_type = "text/plain"
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": content_type
            }
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.post("/download-multiple")
async def download_multiple_files(request: DownloadRequest, user_info: dict = Depends(verify_token)):
    """Download multiple SSL files as a ZIP archive."""
    try:
        # Validate filenames
        for filename in request.filenames:
            if not filename or ".." in filename or "/" in filename:
                raise HTTPException(status_code=400, detail=f"Invalid filename: {filename}")
        
        # Create ZIP archive
        zip_path = ssl_manager.create_zip_archive(request.filenames)
        
        # Read ZIP file
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        # Clean up ZIP file
        try:
            os.unlink(zip_path)
        except:
            pass  # Best effort cleanup
        
        return Response(
            content=zip_content,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={os.path.basename(zip_path)}",
                "Content-Type": "application/zip"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP archive: {str(e)}")


@router.delete("/files/{filename}")
async def delete_file(filename: str, request: FileDeleteRequest, user_info: dict = Depends(verify_token)):
    """Delete an SSL file with confirmation."""
    try:
        # Security validation
        if not filename or ".." in filename or "/" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Validate filename matches request
        if filename != request.filename:
            raise HTTPException(status_code=400, detail="Filename mismatch")
        
        # Delete file with confirmation
        ssl_manager.delete_file(filename, request.confirmation)
        
        return {
            "success": True,
            "message": f"File {filename} deleted successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/file-content/{filename}")
async def get_file_content(filename: str, user_info: dict = Depends(verify_token)):
    """Get the content of an SSL file for preview."""
    try:
        # Security validation
        if not filename or ".." in filename or "/" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        content = ssl_manager.get_file_content(filename)
        
        return {
            "success": True,
            "filename": filename,
            "content": content
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.post("/cleanup")
async def cleanup_temp_files(user_info: dict = Depends(verify_token)):
    """Clean up temporary files manually."""
    try:
        ssl_manager.cleanup_temp_files()
        
        return {
            "success": True,
            "message": "Temporary files cleaned up successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup files: {str(e)}")


@router.get("/info")
async def ssl_info(user_info: dict = Depends(verify_token)):
    """Get SSL configuration information."""
    try:
        files = ssl_manager.list_ssl_files()
        
        return {
            "success": True,
            "ssl_directory": str(ssl_manager.ssl_dir),
            "total_files": len(files),
            "files_by_type": {
                "private_keys": len([f for f in files if f['type'] == 'Private Key']),
                "csrs": len([f for f in files if f['type'] == 'Certificate Signing Request']),
                "certificates": len([f for f in files if f['type'] == 'Certificate']),
                "pem_files": len([f for f in files if f['type'] == 'PEM Certificate/Key'])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get SSL info: {str(e)}")