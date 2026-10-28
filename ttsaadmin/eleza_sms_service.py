"""
Eleza SMS API Service for sending SMS messages

API Documentation:
- Transactional SMS: POST /v1/sms/transactional
- Personalized SMS: POST /v1/sms/personalized
- Broadcast SMS: POST /v1/sms/broadcast

Authentication: API Key in headers
"""

import requests
import logging
from typing import List, Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class ElezaSMSError(Exception):
    """Custom exception for Eleza SMS API errors"""
    pass


class ElezaSMSService:
    """Service class for interacting with Eleza SMS API"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Eleza SMS service

        Args:
            api_key: Eleza SMS API key. If not provided, uses from settings
        """
        self.api_key = api_key or getattr(settings, 'ELEZA_SMS_API_KEY', None)
        if not self.api_key:
            raise ElezaSMSError('ELEZA_SMS_API_KEY is not configured in settings')
        self.base_url = getattr(settings, 'ELEZA_SMS_BASE_URL', 'https://api.elezasms.com')
        self.timeout = getattr(settings, 'ELEZA_SMS_TIMEOUT', 30)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
    
    def _make_request(self, endpoint: str, data: Dict) -> Dict:
        """
        Make a request to Eleza SMS API

        Args:
            endpoint: API endpoint (e.g., '/v1/sms/broadcast')
            data: Request payload

        Returns:
            API response as dictionary

        Raises:
            ElezaSMSError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.post(
                url,
                json=data,
                headers=self._get_headers(),
                timeout=self.timeout
            )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Eleza SMS API request failed: {str(e)}")
            logger.error(f"URL: {url}")
            logger.error(f"Data: {data}")
            raise ElezaSMSError(f"API request failed: {str(e)}")
    
    def send_transactional_sms(
        self,
        phone_number: str,
        message: str,
        sender_id: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> Dict:
        """
        Send a transactional SMS to a single recipient

        Args:
            phone_number: Recipient phone number (with country code, e.g., +254700123456)
            message: SMS message content
            sender_id: Optional sender ID (default from settings)
            callback_url: Optional callback URL for delivery status

        Returns:
            API response with message ID and status
        """
        sender_id = sender_id or getattr(settings, 'ELEZA_SMS_SENDER_ID', 'Cambridge')

        data = {
            'sender_id': sender_id,
            'message': message,
            'recipient': phone_number.replace('+', ''),  # Remove + for Eleza API
        }

        if callback_url:
            data['callback_url'] = callback_url

        logger.info(f"Sending transactional SMS to {phone_number}")
        return self._make_request('/v1/sms/transactional', data)
    
    def send_personalized_sms(
        self,
        messages: List[Dict[str, str]],
        sender_id: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> Dict:
        """
        Send personalized SMS messages to multiple recipients

        Args:
            messages: List of dictionaries with 'recipient' (or 'phone_number') and 'message' keys.
                      Optionally includes 'name' for logging purposes.
            sender_id: Optional sender ID (default from settings)
            callback_url: Optional callback URL for delivery status

        Returns:
            API response with message IDs and status

        Example:
            messages = [
                {'recipient': '254700123456', 'message': 'Hello John, your tournament is on Dec 15'},
                {'recipient': '254700123457', 'message': 'Hello Jane, your tournament is on Dec 15'},
            ]
        """
        sender_id = sender_id or getattr(settings, 'ELEZA_SMS_SENDER_ID', 'Cambridge')

        # Convert phone_number to recipient and remove + prefix
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                'recipient': msg.get('recipient', msg.get('phone_number', '')).replace('+', ''),
                'message': msg.get('message', '')
            }
            formatted_messages.append(formatted_msg)

        data = {
            'sender_id': sender_id,
            'data': formatted_messages,
        }

        if callback_url:
            data['callback_url'] = callback_url

        logger.info(f"Sending personalized SMS to {len(messages)} recipients")
        return self._make_request('/v1/sms/personalized', data)
    
    def send_broadcast_sms(
        self,
        phone_numbers: List[str],
        message: str,
        sender_id: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> Dict:
        """
        Send a broadcast SMS to multiple recipients

        Args:
            phone_numbers: List of recipient phone numbers
            message: SMS message content (same for all recipients)
            sender_id: Optional sender ID (default from settings)
            callback_url: Optional callback URL for delivery status

        Returns:
            API response with message ID and status
        """
        sender_id = sender_id or getattr(settings, 'ELEZA_SMS_SENDER_ID', 'Cambridge')

        # Remove + prefix from phone numbers for Eleza API
        formatted_recipients = [phone.replace('+', '') for phone in phone_numbers]

        data = {
            'sender_id': sender_id,
            'message': message,
            'recipients': formatted_recipients,
        }

        if callback_url:
            data['callback_url'] = callback_url

        logger.info(f"Sending broadcast SMS to {len(phone_numbers)} recipients")
        return self._make_request('/v1/sms/broadcast', data)
    
    def validate_phone_number(self, phone_number: str) -> str:
        """
        Validate and format phone number
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            Formatted phone number with country code
            
        Raises:
            ElezaSMSError: If phone number is invalid
        """
        # Remove spaces, dashes, and parentheses
        cleaned = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        # Ensure it starts with +
        if not cleaned.startswith('+'):
            # Assume Kenya if no country code
            if cleaned.startswith('0'):
                cleaned = '+254' + cleaned[1:]
            elif cleaned.startswith('7'):
                cleaned = '+254' + cleaned
            else:
                cleaned = '+' + cleaned
        
        # Validate Kenya phone numbers (starts with +254 and is 12-13 digits)
        if cleaned.startswith('+254'):
            if len(cleaned) not in [12, 13]:
                raise ElezaSMSError(f"Invalid Kenya phone number: {phone_number}")
        else:
            # For other countries, basic validation (10-15 digits with +)
            if len(cleaned) < 10 or len(cleaned) > 16:
                raise ElezaSMSError(f"Invalid phone number: {phone_number}")
        
        return cleaned


# Lazy singleton instance for easy import
def get_eleza_sms_service():
    """Get or create the Eleza SMS service singleton instance"""
    if not hasattr(get_eleza_sms_service, '_instance'):
        try:
            get_eleza_sms_service._instance = ElezaSMSService()
        except ElezaSMSError:
            # If API key is not configured, return None
            get_eleza_sms_service._instance = None
    return get_eleza_sms_service._instance

# For backward compatibility, but this will be None if API key is not configured
eleza_sms_service = get_eleza_sms_service()
