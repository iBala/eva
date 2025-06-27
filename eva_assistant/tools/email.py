"""
Gmail tools for Eva Assistant.

Provides email sending capabilities for Eva to communicate on behalf of the user:
- Send emails from Eva's account
- Draft emails for review
- Handle professional email formatting
"""

import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from eva_assistant.tools.base import ToolABC
from eva_assistant.auth.eva_auth import EvaAuthManager

logger = logging.getLogger(__name__)


# Pydantic schemas for email tool arguments

class SendEmailArgs(BaseModel):
    """Arguments for sending an email."""
    to: List[str] = Field(..., description="List of recipient email addresses")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body content")
    cc: List[str] = Field(default_factory=list, description="CC recipients")
    bcc: List[str] = Field(default_factory=list, description="BCC recipients")
    reply_to: Optional[str] = Field(None, description="Reply-to email address if different from sender")


class DraftEmailArgs(BaseModel):
    """Arguments for creating an email draft."""
    to: List[str] = Field(..., description="List of recipient email addresses")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body content")
    cc: List[str] = Field(default_factory=list, description="CC recipients")
    bcc: List[str] = Field(default_factory=list, description="BCC recipients")


class GetContactArgs(BaseModel):
    """Arguments for looking up contact information."""
    name: str = Field(..., description="Contact name to search for")
    email_domain: Optional[str] = Field(None, description="Email domain to search within")


# Email Tools Implementation

class SendEmailTool(ToolABC):
    """Send an email from Eva's Gmail account."""
    
    name = "send_email"
    description = "Send an email from Eva's account on behalf of the user"
    schema = SendEmailArgs
    returns = lambda result: f"Email sent to {', '.join(result.get('recipients', []))}"
    
    async def run(self, args: SendEmailArgs) -> Dict[str, Any]:
        """Send an email using Eva's Gmail account (backward compatibility)."""
        return await self.run_with_context(args, {})
    
    async def run_with_context(self, args: SendEmailArgs, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email using Eva's Gmail account with user context."""
        try:
            # Get boss name from context for signature
            boss_name = context.get('boss_name')
            if not boss_name:
                # Try to get from primary user context
                primary_user_id = context.get('primary_user_id', 'founder')
                try:
                    from eva_assistant.agent.prompts import get_user_context
                    user_context = get_user_context(primary_user_id)
                    boss_name = user_context.get('boss_name')
                except Exception:
                    boss_name = None
            
            # Use Eva's dedicated auth manager for sending emails
            eva_auth = EvaAuthManager()
            service = await eva_auth.get_gmail_service()
            
            # Create the email message with boss name for signature
            message = self._create_email_message(
                to=args.to,
                subject=args.subject,
                body=args.body,
                cc=args.cc,
                bcc=args.bcc,
                reply_to=args.reply_to,
                boss_name=boss_name
            )
            
            # Send the email
            result = service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logger.info(f"Email sent successfully to {args.to}, message ID: {result.get('id')} (boss: {boss_name})")
            
            return {
                'success': True,
                'message_id': result.get('id'),
                'recipients': args.to,
                'subject': args.subject,
                'thread_id': result.get('threadId'),
                'boss_name': boss_name,
                'message': 'Email sent successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to send email to {args.to}: {e}")
            return {
                'success': False,
                'error': str(e),
                'recipients': args.to,
                'message': 'Failed to send email'
            }
    
    def _create_email_message(self, to: List[str], subject: str, body: str, 
                             cc: List[str] = None, bcc: List[str] = None, 
                             reply_to: str = None, boss_name: str = None) -> Dict[str, str]:
        """Create an email message in the format expected by Gmail API."""
        
        # Create MIME message
        msg = MIMEMultipart('alternative')
        msg['To'] = ', '.join(to)
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = ', '.join(cc)
        if bcc:
            msg['Bcc'] = ', '.join(bcc)
        if reply_to:
            msg['Reply-To'] = reply_to
        
        # Add signature to body with boss name
        body_with_signature = self._add_signature(body, boss_name)
        
        # Attach plain text version
        text_part = MIMEText(body_with_signature, 'plain')
        msg.attach(text_part)
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        
        return {'raw': raw_message}
    
    def _add_signature(self, body: str, boss_name: str = None) -> str:
        """Add Eva's professional signature to the email."""
        if boss_name:
            signature = f"\n\nBest regards,\nEva\nExecutive Assistant to {boss_name}"
        else:
            signature = "\n\nBest regards,\nEva\nExecutive Assistant"
        
        # Add signature if not already present
        if "Best regards,\nEva" not in body and "Best,\nEva" not in body:
            return body + signature
        
        return body


class DraftEmailTool(ToolABC):
    """Create an email draft for review before sending."""
    
    name = "draft_email"
    description = "Create an email draft that can be reviewed before sending"
    schema = DraftEmailArgs
    returns = lambda result: f"Draft created for: {result.get('subject', 'No subject')}"
    
    async def run(self, args: DraftEmailArgs) -> Dict[str, Any]:
        """Create an email draft in Eva's Gmail account (backward compatibility)."""
        return await self.run_with_context(args, {})
    
    async def run_with_context(self, args: DraftEmailArgs, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create an email draft in Eva's Gmail account with user context."""
        try:
            # Get boss name from context for signature
            boss_name = context.get('boss_name')
            if not boss_name:
                # Try to get from primary user context
                primary_user_id = context.get('primary_user_id', 'founder')
                try:
                    from eva_assistant.agent.prompts import get_user_context
                    user_context = get_user_context(primary_user_id)
                    boss_name = user_context.get('boss_name')
                except Exception:
                    boss_name = None
            
            # Use Eva's dedicated auth manager for creating drafts
            eva_auth = EvaAuthManager()
            service = await eva_auth.get_gmail_service()
            
            # Create the email message with boss name for signature
            send_tool = SendEmailTool()
            message = send_tool._create_email_message(
                to=args.to,
                subject=args.subject,
                body=args.body,
                cc=args.cc,
                bcc=args.bcc,
                boss_name=boss_name
            )
            
            # Create draft
            draft_body = {'message': message}
            draft = service.users().drafts().create(
                userId='me',
                body=draft_body
            ).execute()
            
            logger.info(f"Email draft created for {args.to}, draft ID: {draft.get('id')} (boss: {boss_name})")
            
            return {
                'success': True,
                'draft_id': draft.get('id'),
                'message_id': draft.get('message', {}).get('id'),
                'recipients': args.to,
                'subject': args.subject,
                'boss_name': boss_name,
                'message': 'Draft created successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to create email draft for {args.to}: {e}")
            return {
                'success': False,
                'error': str(e),
                'recipients': args.to,
                'message': 'Failed to create draft'
            }


class GetContactTool(ToolABC):
    """Look up contact information from previous emails or calendar events."""
    
    name = "get_contact_info"
    description = "Look up contact information by name or email domain"
    schema = GetContactArgs
    returns = lambda result: f"Found {len(result.get('contacts', []))} contacts"
    
    async def run(self, args: GetContactArgs) -> Dict[str, Any]:
        """Look up contact information from Gmail."""
        try:
            # Use Eva's dedicated auth manager for accessing Gmail
            eva_auth = EvaAuthManager()
            service = await eva_auth.get_gmail_service()
            
            # Search for emails containing the contact name
            query = f'from:{args.name} OR to:{args.name}'
            if args.email_domain:
                query += f' OR from:@{args.email_domain} OR to:@{args.email_domain}'
            
            # Get recent messages
            messages_result = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()
            
            messages = messages_result.get('messages', [])
            contacts = []
            seen_emails = set()
            
            # Extract contact information from messages
            for message in messages:
                msg_detail = service.users().messages().get(
                    userId='me',
                    id=message['id']
                ).execute()
                
                headers = msg_detail.get('payload', {}).get('headers', [])
                
                # Extract email addresses from headers
                for header in headers:
                    name = header.get('name', '').lower()
                    if name in ['from', 'to', 'cc']:
                        email_addr = header.get('value', '')
                        
                        # Parse email address
                        if '<' in email_addr:
                            # Format: "Name <email@domain.com>"
                            parts = email_addr.split('<')
                            contact_name = parts[0].strip().strip('"')
                            email = parts[1].strip('>')
                        else:
                            # Format: "email@domain.com"
                            contact_name = email_addr.split('@')[0]
                            email = email_addr
                        
                        if email not in seen_emails and '@' in email:
                            contacts.append({
                                'name': contact_name,
                                'email': email
                            })
                            seen_emails.add(email)
            
            logger.info(f"Found {len(contacts)} contacts for query: {args.name}")
            
            return {
                'success': True,
                'contacts': contacts,
                'query': args.name,
                'count': len(contacts)
            }
            
        except Exception as e:
            logger.error(f"Failed to get contact info for {args.name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'contacts': [],
                'query': args.name
            } 