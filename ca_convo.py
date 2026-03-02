"""Interactive CLI chat with AI tax assistant, supporting file attachments.

Usage examples:
  # Start interactive conversation
  python file_analysis.py

  # Chat with file attachments
  python file_analysis.py -f data/samples/form16_complex.txt

  # Non-interactive single question
  python file_analysis.py -q "What deductions am I eligible for?" -f form16.pdf

Features:
  * Interactive chat loop with conversation history
  * File attachment support: .txt, .csv, .md, .pdf, .png, .jpg, .jpeg
  * PDF text extraction via PyPDF2
  * Image base64 encoding for multimodal models
  * Loads system prompt from docs/system_prompt.md with fallback
  * Environment configuration via .env file

Commands during chat:
  /exit or /quit - Exit chat
  /reset - Clear conversation history
  /attach <file> - Attach a file to next message
  /files - List currently attached files
  /clear-files - Clear all attached files
"""

from __future__ import annotations
import os, argparse, base64, sys
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from azure_openai import create_client, get_deployment_name

load_dotenv()

SUPPORTED_TEXT_EXT = {'.txt', '.csv', '.md'}
SUPPORTED_PDF_EXT = {'.pdf'}
SUPPORTED_IMG_EXT = {'.png', '.jpg', '.jpeg'}

def load_system_prompt() -> str:
	path = os.environ.get("SYSTEM_PROMPT_PATH", "docs/system_prompt.md")
	if not os.path.exists(path):
		return ("You are an expert Indian Chartered Accountant–style AI Tax Assistant. "
				"If information is missing ask clarifying questions. End with a disclaimer.")
	with open(path, 'r', encoding='utf-8') as f:
		content = f.read()
	# Extract first occurrence of the primary role paragraph
	marker = "You are an expert Indian Chartered Accountant"
	if marker in content:
		seg = content.split(marker, 1)[1]
		seg = marker + seg
		# Trim at first heading after body
		for stop in ["CORE OBJECTIVES", "MANDATORY CLARIFYING"]:
			idx = seg.find(stop)
			if idx != -1:
				seg = seg[:idx]
				break
		return seg.strip()
	return content[:4000]

def read_file_payload(path: str) -> Dict[str, Any]:
	ext = os.path.splitext(path)[1].lower()
	if ext in SUPPORTED_TEXT_EXT:
		with open(path, 'r', encoding='utf-8', errors='ignore') as f:
			return {"type":"text","name":os.path.basename(path),"content":f.read()}
	if ext in SUPPORTED_PDF_EXT:
		try:
			import PyPDF2  # optional
			text_parts = []
			with open(path, 'rb') as f:
				reader = PyPDF2.PdfReader(f)
				for page in reader.pages:
					try:
						text_parts.append(page.extract_text() or "")
					except Exception:
						pass
			return {"type":"pdf","name":os.path.basename(path),"content":"\n".join(text_parts).strip()}
		except Exception:
			with open(path, 'rb') as f:
				data = base64.b64encode(f.read()).decode('ascii')
			return {"type":"pdf-bytes","name":os.path.basename(path),"data":data}
	if ext in SUPPORTED_IMG_EXT:
		with open(path, 'rb') as f:
			data = base64.b64encode(f.read()).decode('ascii')
		return {"type":"image","name":os.path.basename(path),"data":data}
	raise ValueError(f"Unsupported file type: {path}")

class ChatSession:
    """Manages conversation state and file attachments for the chat session."""
    
    def __init__(self, client, system_prompt: str):
        self.client = client
        self.model = get_deployment_name()
        self.system_prompt = system_prompt
        self.history: List[Dict[str, str]] = []
        self.attached_files: List[Dict[str, Any]] = []
        self.max_history = 20  # Keep last 20 messages
    
    def add_file(self, file_path: str) -> bool:
        """Attach a file to the session. Returns True if successful."""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
        
        try:
            file_data = read_file_payload(file_path)
            # Check if already attached
            for existing in self.attached_files:
                if existing.get('path') == file_path:
                    print(f"📎 File already attached: {os.path.basename(file_path)}")
                    return True
            
            file_data['path'] = file_path
            self.attached_files.append(file_data)
            print(f"📎 Attached: {os.path.basename(file_path)} ({file_data['type']})")
            return True
        except Exception as e:
            print(f"❌ Error attaching {file_path}: {e}")
            return False
    
    def clear_files(self):
        """Clear all attached files."""
        self.attached_files.clear()
        print("🗑️ Cleared all attached files")
    
    def list_files(self):
        """Show currently attached files."""
        if not self.attached_files:
            print("📋 No files attached")
        else:
            print("📋 Attached files:")
            for i, f in enumerate(self.attached_files, 1):
                name = f.get('name', 'unknown')
                ftype = f.get('type', 'unknown')
                print(f"  {i}. {name} ({ftype})")
    
    def send_message(self, user_input: str) -> str:
        """Send a message and get response, including any attached files."""
        user_message = self._build_user_message(user_input)
        
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self._call_model(messages)
            
            # Update history
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "assistant", "content": response})
            
            # Trim history if needed
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
            
            return response
            
        except Exception as e:
            return f"❌ Error calling model: {e}"
    
    def _build_user_message(self, user_input: str) -> str:
        """Build the complete user message including file contents."""
        parts = [user_input.strip()]
        
        if self.attached_files:
            parts.append("\n--- ATTACHED DOCUMENTS ---")
            for file_data in self.attached_files:
                if file_data['type'] in {"text", "pdf"}:
                    content = file_data['content'][:3000]  # Truncate long files
                    if len(file_data['content']) > 3000:
                        content += "\n... (truncated)"
                    parts.append(f"\n📄 {file_data['name']} ({file_data['type']}):\n{content}")
                else:
                    parts.append(f"\n🖼️ {file_data['name']} ({file_data['type']}): Binary data attached")
        
        return "\n".join(parts)
    
    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        """Call the OpenAI model with fallback handling."""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=messages,
                max_tokens=1200
            )
            return resp.choices[0].message.content
        except Exception as e:
            # Fallback for different API versions
            try:
                resp = self.client.responses.create(
                    model=self.model,
                    input=messages,
                    temperature=0,
                    max_output_tokens=1200
                )
                return resp.output_text
            except Exception:
                raise e
    
    def reset_history(self):
        """Clear conversation history but keep files."""
        self.history.clear()
        print("🔄 Conversation history cleared")

def interactive_chat(session: ChatSession):
    """Main interactive chat loop."""
    print("💬 AI Tax Assistant Chat")
    print("Commands: /exit, /quit, /reset, /attach <file>, /files, /clear-files")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n🔵 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.lower() in {"/exit", "/quit"}:
            print("👋 Goodbye!")
            break
        elif user_input.lower() == "/reset":
            session.reset_history()
            continue
        elif user_input.lower() == "/files":
            session.list_files()
            continue
        elif user_input.lower() == "/clear-files":
            session.clear_files()
            continue
        elif user_input.lower().startswith("/attach "):
            file_path = user_input[8:].strip()
            session.add_file(file_path)
            continue
        
        # Send message and get response
        print("🤔 Thinking...")
        response = session.send_message(user_input)
        print(f"\n🤖 Assistant:\n{response}")

def single_question_mode(session: ChatSession, question: str) -> str:
    """Handle single question without interactive loop."""
    return session.send_message(question)

def main():
    parser = argparse.ArgumentParser(description="AI Tax Assistant Chat with File Support")
    parser.add_argument('-q', '--question', help='Single question (non-interactive)')
    parser.add_argument('-f', '--file', action='append', help='Attach file(s) - can be used multiple times')
    parser.add_argument('--model', default=os.environ.get('CHAT_MODEL', 'gpt-4o-mini'))
    args = parser.parse_args()

    try:
        client = create_client()
    except Exception as e:
        print(f"❌ Failed to create OpenAI client: {e}")
        print("💡 Check your .env file for AZURE_OPENAI_* or OPENAI_API_KEY settings")
        sys.exit(1)

    system_prompt = load_system_prompt()
    session = ChatSession(client, system_prompt)

    # Attach any files specified on command line
    if args.file:
        for file_path in args.file:
            session.add_file(file_path)

    # Single question mode
    if args.question:
        print("🤔 Processing your question...")
        response = single_question_mode(session, args.question)
        print(f"\n🤖 Assistant:\n{response}")
        return

    # Interactive mode (default)
    interactive_chat(session)

if __name__ == "__main__":
    main()

