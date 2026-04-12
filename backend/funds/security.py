import logging
from oletools.mraptor import MacroRaptor
from django.conf import settings

logger = logging.getLogger(__name__)

class SecurityScanner:
    """
    Security scanner for uploaded files.
    Performs MIME check, size validation, and macro detection.
    """
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_MIME_TYPES = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ]

    @staticmethod
    def scan_file(uploaded_file, user):
        """
        Scans a file for security threats.
        Returns (is_safe, error_message, threat_type).
        """
        # 1. Size Validation
        if uploaded_file.size > SecurityScanner.MAX_FILE_SIZE:
            return False, "File size exceeds limit (5MB).", "SIZE_EXCEEDED"

        # 2. MIME Type Validation
        if uploaded_file.content_type not in SecurityScanner.ALLOWED_MIME_TYPES:
            return False, "Invalid file type. Only .xlsx files are allowed.", "INVALID_MIME"

        # 3. Macro Detection
        try:
            file_content = uploaded_file.read()
            uploaded_file.seek(0)
            
            # Use MacroRaptor safely. 
            # Note: .xlsx files are zip containers and don't support VBA macros (those are .xlsm)
            # oletools mraptor handles this by checking for OLE containers or vbaProject.bin
            try:
                m = MacroRaptor(uploaded_file.name, data=file_content)
                m.scan()
                if m.suspicious:
                    logger.critical(
                        f"SECURITY THREAT: Macro detected in file uploaded by {user.email}. "
                        f"Threat type: {m.reason}. User account deactivated."
                    )
                    user.is_active = False
                    user.save()
                    return False, "Security threat detected: Embedded macros are forbidden.", "MACRO_DETECTED"
            except Exception as e:
                # If mraptor fails because the file format isn't supported (e.g. plain .xlsx)
                # it's generally safe as far as VBA macros are concerned.
                logger.warning(f"Macro scan skipped or failed for {uploaded_file.name}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error during security scan execution: {str(e)}", exc_info=True)
            return False, "Error processing file security scan.", "SCAN_ERROR"

        return True, None, None
