# app.py
from flask import Flask, request, jsonify, render_template
import os
from dotenv import load_dotenv
import google.generativeai as genai
import anthropic
import re
import json
import base64
import io
from PyPDF2 import PdfReader

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Using multiple available models for fallbacks
    model_flash = genai.GenerativeModel('gemini-2.0-flash')
    model_pro = genai.GenerativeModel('gemini-flash-latest')
else:
    model_flash = None
    model_pro = None
    print("WARNING: GEMINI_API_KEY not found in .env")

# Configure Anthropic AI
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if ANTHROPIC_API_KEY:
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    anthropic_client = None
    print("WARNING: ANTHROPIC_API_KEY not found in .env")

# Knowledge base for common Indian legal topics
LEGAL_KNOWLEDGE_BASE = {
    "property law": "Property Law in India governs the ownership, transfer, and use of property. It is primarily governed by the Transfer of Property Act, 1882, and includes laws related to movable and immovable property. Key concepts include ownership, possession, and transfer of property rights.",
    "constitutional law": "Constitutional Law in India is based on the Constitution of India adopted in 1950. It defines the structure of the government, the rights and duties of citizens, and the federal system. The Constitution has been amended multiple times and includes provisions for fundamental rights and directive principles.",
    "criminal law": "Criminal Law in India is primarily governed by the Indian Penal Code, 1860 (now Bharatiya Nyaya Sanhita, 2023). It deals with crimes like murder, theft, assault, and other offenses against the state and individuals. The Code of Criminal Procedure, 1973 (now Bharatiya Nagarik Suraksha Sanhita, 2023), provides the procedural framework for criminal cases.",
    "civil law": "Civil Law in India deals with disputes between individuals and organizations. The Indian Contract Act, 1872, governs contracts, while the Civil Procedure Code, 1908, provides the procedural framework. Civil cases include property disputes, family matters, and commercial transactions.",
    "family law": "Family Law in India covers marriage, divorce, custody, inheritance, and succession. Key laws include the Hindu Marriage Act, 1955, the Indian Divorce Act, 1869, and the Succession Act, 1925. Personal laws vary based on religion and community.",
    "contract law": "Contract Law in India is governed by the Indian Contract Act, 1872. A valid contract requires offer, acceptance, consideration, intention to create legal relations, capacity, and legality. Contracts must not violate public policy or be opposed to the law.",
    "corporate law": "Corporate Law in India is regulated by the Companies Act, 2013. It governs the formation, management, and dissolution of companies. Key aspects include board of directors, shareholder rights, corporate governance, and compliance with regulatory requirements.",
    "intellectual property": "Intellectual Property Law in India protects creations like inventions, literary works, and symbols. Key laws include the Patents Act, 1970 (inventions), Copyright Act, 1957 (creative works), and the Trade Marks Act, 1999 (brand names).",
    "labor law": "Labor Law in India protects workers' rights and regulates employment relationships. Key laws include the Industrial Disputes Act, 1947, the Minimum Wages Act, 1948, and the Factories Act, 1948. These laws cover working conditions, safety, and social security.",
    "tax law": "Tax Law in India is governed by the Income Tax Act, 1961 and the Goods and Services Tax Act, 2017. Income tax applies to individuals and corporations on their income, while GST is a consumption tax on goods and services.",
    "consumer protection": "Consumer Protection Law in India is regulated by the Consumer Protection Act, 2019. It protects consumer rights including the right to safety, information, choice, and redressal. Consumer disputes are resolved through consumer courts and commissions.",
    "lease": "A lease of immovable property is a transfer of a right to enjoy such property, made for a certain time, express or implied, or in perpetuity, in consideration of a price paid or promised (Section 105, Transfer of Property Act, 1882).",
    "license": "A license is a right granted by one person to another to do or continue to do, in or upon the immovable property of the grantor, something which would, in the absence of such right, be unlawful (Section 52, Indian Easements Act, 1882).",
}

# Specific Q&A for common legal questions
LEGAL_QA = [
    (("matrimonial", "property"), "In India, matrimonial property disputes are governed by personal laws and the Special Marriage Act, 1954. According to the Hindu Marriage Act and other personal laws, property owned before marriage or acquired individually often remains separate property. However, a spouse may claim maintenance and can seek an equitable share of marital assets during divorce. To protect your separate property, you can: (1) Keep property in your individual name, (2) Create a prenuptial or postnuptial agreement, (3) Document ownership clearly with original purchase deeds proving you acquired the property before marriage, (4) Keep separate bank accounts for inherited or personal property. If you've commingled property or contributed equally, the courts may consider it joint property. Consult a family lawyer for specific advice based on your situation."),
    (("husband", "property"), "As a woman in India, you have equal rights to own, inherit, and dispose of property independently. Under the Hindu Succession Act and the Special Marriage Act, wives have equal inheritance rights as husbands. You cannot be forced to transfer or give your property to anyone. Your property rights include: (1) Right to own property in your individual name, (2) Right to dispose of or sell your property without spouse's permission, (3) Right to exclude property from matrimonial assets if it's separate property, (4) Right to claim maintenance if divorced. For inheritance planning, consider making a will specifying who inherits your property. If facing pressure to transfer property, you can seek legal help."),
    (("wife", "property"), "In India, wives have equal property rights as husbands under personal laws and the Special Marriage Act, 1954. A wife's property rights include: (1) Right to own separate property and dispose of it independently, (2) Right to inherit from parents, siblings, and extended family, (3) Right to claim maintenance from husband during separation/divorce, (4) Possible claim over marital/joint property acquired during marriage, (5) Right to be nominated as a nominee in husband's bank accounts, insurance, or property. Separate property (inherited or acquired before marriage) remains your own. Joint property (acquired during marriage with joint efforts/funds) may be split equitably during divorce. Document your investments and maintain records."),
    (("marriage", "compulsory"), "Marriage is not compulsory in India. The Constitution guarantees the right to marry or remain unmarried. Adults (18+ for women, 21+ for men) can choose to marry or stay single. However, if a person is already married, they are bound by the marriage contract until legally divorced. Some considerations: (1) Parental pressure has no legal authority to force marriage, (2) Child marriages (below 18 for girls) are illegal and attract legal penalties, (3) Forced marriage is a form of domestic violence, (4) You can refuse marriage and pursue any remedies if threatened. If you're facing pressure to marry, you can report it as domestic violence or seek protection from courts."),
    (("forced", "marriage"), "Forced marriage is not allowed under Indian law. It is considered a violation of personal liberty and can be challenged in court. If you are being forced into marriage, you can seek protection through the police, domestic violence courts, or family courts. You may also be able to file a writ petition in the High Court for protection of your fundamental rights."),
    (("no", "marriage"), "Marriage is not a legal obligation in India. Individuals have the freedom to choose whether to marry or remain single. However, if a marriage takes place, it must comply with the relevant marriage laws, and both adults must consent to the marriage."),
    (("divorce",), "Divorce in India is governed by personal laws like the Hindu Marriage Act, 1955. Types of divorce: (1) Divorce by mutual consent - both spouses agree, simpler and faster process, (2) Contested divorce - one spouse seeks grounds like adultery, cruelty, abandonment, desertion. Grounds for divorce include adultery, cruelty, desertion for 2+ years, conversion to another religion, mental disorder, and communicable disease. Process: File petition in family court, serve notice to spouse, attend hearings, court may attempt reconciliation, and if grounds proven, decree granted. In mutual consent divorce, it takes 3-6 months. You can claim maintenance, child custody, and property settlement. Consult a family lawyer for your specific situation."),
    (("custody",), "Child custody in India is governed by the Hindu Minority and Guardianship Act, 1956, and other laws. Key principles: (1) The welfare of the child is paramount, (2) Children below 5 usually stay with mother, (3) Older children may choose if mature enough, (4) Either parent can seek custody. Types: Sole custody (one parent), Joint custody (both parents share), Sole guardianship, Guardianship with access rights. Factors considered: Child's age, health, education, relationship with each parent, ability to provide care, stability, and the child's wishes. Courts prioritize the child's best interests. Both parents have a duty to support the child financially. Custody can be modified if circumstances change significantly."),
    (("inheritance",), "Inheritance in India is governed by personal laws and the Indian Succession Act, 1925. For Hindus, the Hindu Succession Act, 1956 applies. Key points: (1) Children (sons and daughters have equal rights) inherit equally from parents, (2) If no children, parents inherit, then siblings, (3) A will determines inheritance if validly made, (4) Without a will (intestate), succession rules apply, (5) Daughters have equal coparcenary rights in ancestral property. You can make a will to specify inheritance, ensure it's witnessed properly, and registered. Succession taxes may apply depending on amount. Consult a lawyer to understand your succession rights."),
    (("succession",), "Succession Law in India is governed by the Indian Succession Act, 1925, and personal religious laws. Succession deals with transfer of property after death. Two types: (1) Testamentary succession - with a valid will, (2) Intestate succession - no valid will, rules apply. Personal laws vary: Hindu Succession Act for Hindus, Muslim Personal Law for Muslims, Christian law for Christians. A will allows you to specify who inherits your property, appoint executors, and provide for dependents. To make a valid will: State wishes clearly, sign with witnesses, get it registered (optional but recommended). Succession certificate may be needed for property/bank transfers after death."),
    (("maintenance", "alimony"), "Maintenance (alimony) in India is a right to financial support for a spouse. Under laws like the Hindu Marriage Act, 1955 and Section 125 of CrPC, a spouse can claim maintenance if they are unable to support themselves. The amount is determined based on income, living standards, and duration of marriage."),
    (("alimony",), "Alimony in India refers to financial support provided by one spouse to another after separation or divorce. It is based on the earning capacity of both individuals and the needs of the claimant."),
    (("child", "support"), "Child support in India is a legal obligation for both parents to provide for their children's financial needs, including education and healthcare, regardless of their marital status."),
    (("fir", "refused", "police", "register", "complaint"), "If the police refuse to register an FIR (First Information Report) for a cognizable offense like theft, you have legal remedies. Under the Code of Criminal Procedure (CrPC) and the new Bharatiya Nagarik Suraksha Sanhita (BNSS), you can take the following steps:\n\n1. **Approach Higher Authorities**: Send the substance of your information/complaint in writing and by post to the Superintendent of Police (SP) or Deputy Commissioner of Police (DCP).\n2. **Magistrate Complaint**: If the SP/DCP does not act, you can approach the local Judicial Magistrate under Section 156(3) of CrPC (or equivalent BNSS section) to pass an order directing the police to register the FIR and investigate.\n3. **Online Portals**: Use state-specific online police grievance portals like CCTNS.\n4. **High Court**: As a last resort, file a writ petition in the High Court.\nAlways keep proof of your written complaints and postal receipts."),
    (("lease", "license", "difference"), "The key difference between a Lease and a License in Indian law (Transfer of Property Act vs Indian Easements Act) lies in the transfer of interest:\n\n1. **Interest in Property**: A Lease transfers an interest in the property (right to enjoy), whereas a License is a mere permission to use the property without transferring any interest.\n2. **Transferability**: A Lease is generally transferable and heritable. A License is personal and neither transferable nor heritable.\n3. **Possession**: Lease involves transfer of possession. License usually involves only a right to use, with possession remaining with the owner.\n4. **Revocability**: A Lease cannot be revoked at the will of the landlord (except for breach of terms). A License is generally revocable at the will of the grantor.\n5. **Legal Action**: A lessee can sue a third party for trespass; a licensee generally cannot.")
]

# Local Fallback Templates for Drafting
LOCAL_TEMPLATES = {
    "rent agreement": """
# DRAFT: LEAVE AND LICENSE AGREEMENT (RENT AGREEMENT)

**THIS AGREEMENT** is made at [City] on this [Day] day of [Month], [Year].

**BETWEEN:**
[LANDLORD NAME], Residing at [LANDLORD ADDRESS], hereinafter referred to as the 'LICENSOR'.

**AND:**
[TENANT NAME], Residing at [TENANT ADDRESS], hereinafter referred to as the 'LICENSEE'.

**WHEREAS** the Licensor is the absolute owner of the premises situated at:
[PROPERTY ADDRESS] (hereinafter referred to as the 'Licensed Premises').

**NOW THIS AGREEMENT WITNESSETH AS UNDER:**

1. **TERM:** The license is granted for a period of 11 (Eleven) months commencing from [Start Date] and expiring on [End Date].
2. **RENT:** The Licensee shall pay a monthly compensation (Rent) of Rs. [Amount]/- per month.
3. **DEPOSIT:** The Licensee has deposited a sum of Rs. [Deposit_Amount]/- as interest-free Security Deposit.
4. **MAINTENANCE:** The Licensee/Licensee agree to pay Society Maintenance charges as per mutual agreement.
5. **LOCK-IN PERIOD:** There shall be a lock-in period of [X] months.
6. **TERMINATION:** Either party can terminate this agreement by giving [X] month's notice in writing.
7. **USE:** The premises shall be used only for residential purposes and no subletting is allowed.

**IN WITNESS WHEREOF** the parties have signed this agreement on the day and year first above written.

(LICENSOR) ____________________  
(LICENSEE) ____________________
""",
    "legal notice": """
# DRAFT: LEGAL NOTICE

Date: [Date]

To,
[Recipient Name]
[Recipient Address]

**Subject: Legal Notice for [Reason, e.g., Recovery of Dues / Defamation / Breach of Contract]**

Dear Sir/Madam,

Under instructions from and on behalf of my client [Client Name], resident of [Client Address], I hereby serve you with the following legal notice:

1. That you entered into an agreement/transaction with my client on [Date] regarding [Description].
2. That as per the terms of said agreement, you were supposed to [Action Expected].
3. However, you have failed to comply with the terms and have [Description of Breach].
4. My client has repeatedly requested you to [Action Sought], but you have neglected the same.

Therefore, I hereby call upon you to [Demand, e.g., pay the sum of Rs. X] within 15 days from the receipt of this notice, failing which my client will be constrained to initiate appropriate legal proceedings against you in a court of competent jurisdiction at your risk and cost.

Copy of this notice is retained in my office for future record and reference.

Yours faithfully,
[Lawyer Name / Client Name]
"""
}

# Persistence helpers
STORAGE_FILE = 'conversations.json'

def load_conversations():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading conversations: {e}")
            return {}
    return {}

def save_conversations():
    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving conversations: {e}")

# Dictionary to store conversation history
conversations = load_conversations()

@app.route('/')
def index():
    return render_template('index.html')

def normalize_text(text):
    return re.sub(r'[^a-z0-9\s]', '', text.lower())

def extract_text_from_pdf(file_stream):
    try:
        reader = PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""

def find_best_response(message):
    normalized = normalize_text(message)

    # Check specific Q&A matches first (strict)
    for keywords, response in LEGAL_QA:
        if all(keyword in normalized for keyword in keywords):
            return response

    # Next, check broader keyword matches from Q&A (only for multi-word keywords)
    for keywords, response in LEGAL_QA:
        if len(keywords) > 1 and any(keyword in normalized for keyword in keywords):
            # Only return if at least 2 keywords match or if it's very specific
            match_count = sum(1 for keyword in keywords if keyword in normalized)
            if match_count >= 2:
                return response

    # Next, check general topic matches
    for topic, response in LEGAL_KNOWLEDGE_BASE.items():
        if topic in normalized:
            return response

    return None

def get_ai_response(user_message, history, files=None, language="English"):
    system_prompt = (
        f"You are a legal assistant specialized in Indian law. You are currently communicating in {language}. "
        "When answering any legal query, follow this structure strictly:\n\n"
        "1. CLASSIFY THE CASE\n"
        "* Start by identifying what type of case it is (e.g., cheating, theft, harassment).\n"
        "* Use cautious language like: \"This appears to be a case of...\"\n\n"
        "2. PRIMARY LAW (MOST IMPORTANT)\n"
        "* Mention the most relevant law/section first.\n"
        "* Clearly mark it as the main applicable section.\n\n"
        "3. SECONDARY / CONDITIONAL LAWS\n"
        "* Only include additional sections if they truly apply.\n"
        "* Use conditional language like: \"This may also apply if...\" or \"In cases where...\"\n"
        "* Do NOT overgeneralize laws.\n\n"
        "4. EXPLAIN IN SIMPLE TERMS\n"
        "* Briefly explain what the law means in plain English (or the target language).\n\n"
        "5. PRACTICAL NEXT STEPS\n"
        "* Provide clear, step-by-step actions (FIR, cyber complaint, etc.).\n\n"
        "6. JURISDICTION\n"
        "* Use only Indian laws (IPC/BNS, IT Act, etc.).\n"
        "* Mention both IPC and BNS carefully where relevant: \"Previously under IPC..., now under BNS...\"\n\n"
        "7. AVOID OVERCONFIDENCE\n"
        "* Never assume facts not given. If details are missing, ask clarifying questions.\n\n"
        "8. SAFETY & ETHICS\n"
        "* Do not assist in illegal actions, only legal information and guidance.\n\n"
        "DRAFTING MODE:\n"
        "If the user asks to draft a document (like a Rent Agreement or Power of Attorney), you enter 'DRAFTING MODE'. In this mode:\n"
        "1. Complete the full draft BEFORE adding any explanations or notes.\n"
        "2. Do NOT use the 8-point legal advice structure.\n"
        "3. Ask only ONE or TWO questions at a time to gather the necessary details (e.g., names of parties, property address, duration, rent amount).\n"
        "4. Be conversational and guide the user through the process.\n"
        "5. Once all information is collected, generate a professionally formatted legal document draft using Indian legal standards.\n"
        "6. Clearly mark the final output as a 'DRAFT' and advise the user to have it reviewed by a professional before execution.\n\n"
        "STRICT TASK FOCUS & CONTEXT RULES:\n"
        "1. Always stay within the user's requested task. Do NOT introduce unrelated legal topics, even if keywords overlap.\n"
        "2. Interpret terms based on context. For example:\n"
        "   - 'Maintenance' in a rental/property context refers to society charges, utility bills, or upkeep costs.\n"
        "   - 'Maintenance' in a family law context refers to alimony or financial support for a spouse, child, or parent.\n"
        "3. Do not switch topics mid-response.\n\n"
        "Tone:\n"
        "* Clear, calm, and helpful\n"
        "* Not overly dramatic or absolute\n"
        "* Avoid statements like \"This definitely applies\" unless certain\n"
        "* Always include a disclaimer that this is not professional legal advice.\n"
        "If the user has provided a document (PDF or Image), analyze it thoroughly and provide insights based on its content."
    )

    # Process files for Claude
    content_list = []
    
    # Add text message
    content_list.append({"type": "text", "text": user_message})

    # Add images to content_list for Claude
    if files:
        for f in files:
            if f['type'].startswith('image/'):
                content_list.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f['type'],
                        "data": f['data']
                    }
                })
            elif f['type'] == 'application/pdf':
                # PDF text is already appended to user_message in chat() for simplicity
                pass

    # AI Model Chain
    # Try Claude first if client exists
    if anthropic_client:
        try:
            messages = []
            # Filter and alternate roles to ensure Claude compatibility
            last_role = None
            for msg in history[-10:]:
                role = "user" if msg['role'] == 'user' else "assistant"
                if role != last_role:
                    messages.append({"role": role, "content": msg['content']})
                    last_role = role
            
            # Ensure the last message is from the user
            if not messages or messages[-1]['role'] == 'assistant':
                messages.append({"role": "user", "content": content_list})
            else:
                # If the last message was already user, merge it with current content if possible or just replace
                messages[-1]['content'] = content_list

            response = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=2048,
                system=system_prompt,
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            import traceback
            print(f"Anthropic Error (skipping to fallback): {e}")
            traceback.print_exc()

    # Fallback to Gemini Pro (Intelligence)
    if model_pro:
        try:
            chat_context = []
            for msg in history[-10:]:
                role = "user" if msg['role'] == 'user' else "model"
                chat_context.append({"role": role, "parts": [msg['content']]})
            
            chat = model_pro.start_chat(history=chat_context[:-1] if chat_context else [])
            prompt = f"{system_prompt}\n\nUser Question: {user_message}"
            response = chat.send_message(prompt)
            return response.text
        except Exception as e:
            import traceback
            print(f"Gemini Pro Error (skipping to fallback): {e}")
            traceback.print_exc()

    # Fallback to Gemini Flash (Speed/Secondary Quota)
    if model_flash:
        try:
            chat_context = []
            for msg in history[-10:]:
                role = "user" if msg['role'] == 'user' else "model"
                chat_context.append({"role": role, "parts": [msg['content']]})
            
            chat = model_flash.start_chat(history=chat_context[:-1] if chat_context else [])
            prompt = f"{system_prompt}\n\nUser Question: {user_message}"
            response = chat.send_message(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini Flash Error (skipping to local fallback): {e}")

    # Final Fallback to Local Knowledge Base & Templates
    return get_local_fallback_response(user_message)

def extract_template_details(text):
    details = {}
    lower_text = text.lower()
    
    # Extract Amounts (Rent/Deposit) using currency symbols for exact matches
    amounts = re.findall(r'(?:₹|rs\.?|rupees)\s*(\d[\d,]*)', lower_text)
    if len(amounts) >= 2:
        val1 = int(amounts[0].replace(',', ''))
        val2 = int(amounts[1].replace(',', ''))
        details['[Amount]'] = f"{min(val1, val2):,}"
        details['[Deposit_Amount]'] = f"{max(val1, val2):,}"
    elif len(amounts) == 1:
        details['[Amount]'] = amounts[0]
        details['[Deposit_Amount]'] = amounts[0]

    # Extract Names (Landlord/Tenant)
    # Stop capturing at first comma, period, newline, or the word 'and'/'rent'
    landlord_match = re.search(r'landlord(?: name)? (?:is|:) (.*?)(?:\b(?:and|rent|deposit)\b|[\.\,\n]|$)', lower_text)
    if landlord_match:
        details['[LANDLORD NAME]'] = landlord_match.group(1).strip().title()

    tenant_match = re.search(r'tenant(?: name)? (?:is|:) (.*?)(?:\b(?:and|rent|deposit)\b|[\.\,\n]|$)', lower_text)
    if tenant_match:
        details['[TENANT NAME]'] = tenant_match.group(1).strip().title()

    # Extract Tenure
    tenure_match = re.search(r'(\d+)\s*months', lower_text)
    if tenure_match:
        details['11 (Eleven)'] = f"{tenure_match.group(1)} ({tenure_match.group(1)})"
        details['11'] = tenure_match.group(1)

    # Extract Address
    address_match = re.search(r'(?:flat|property|premises).*?(?:in|at) (.*?)(?:[\.\,\n]|\b(?:landlord|tenant)\b|$)', text, re.IGNORECASE)
    if address_match:
        details['[PROPERTY ADDRESS]'] = address_match.group(1).strip().title()

    return details

def fill_template(template, details):
    # Fill in provided details
    for placeholder, value in details.items():
        template = template.replace(placeholder, value)
        
    # Replace remaining standard placeholders with blank lines
    blank_placeholders = [
        '[City]', '[Day]', '[Month]', '[Year]', '[Start Date]', '[End Date]',
        '[X]', '[LANDLORD ADDRESS]', '[TENANT ADDRESS]', '[Amount]', '[Deposit_Amount]',
        '[LANDLORD NAME]', '[TENANT NAME]', '[PROPERTY ADDRESS]', '[Date]',
        '[Recipient Name]', '[Recipient Address]', '[Reason, e.g., Recovery of Dues / Defamation / Breach of Contract]',
        '[Description]', '[Action Expected]', '[Description of Breach]', '[Action Sought]',
        '[Demand, e.g., pay the sum of Rs. X]', '[Lawyer Name / Client Name]', '[Client Name]', '[Client Address]'
    ]
    for p in blank_placeholders:
        template = template.replace(p, "____________________")
        
    return template

def get_local_fallback_response(message):
    lower_msg = message.lower()
    
    template_key = None
    if "rent agreement" in lower_msg:
        template_key = "rent agreement"
    elif "legal notice" in lower_msg:
        template_key = "legal notice"
    
    if template_key:
        template = LOCAL_TEMPLATES[template_key]
        details = extract_template_details(message)
        template = fill_template(template, details)
        return f"NOTICE: My AI cores are currently experiencing high traffic. I have extracted the details from your message and prepared this **Local Template** for you:\n\n{template}"
    
    # Generic local response
    local_resp = find_best_response(message)
    if local_resp:
        return "NOTICE: AI services are currently limited. Based on my offline knowledge: " + local_resp

    # Check for multi-turn drafting context (if they mentioned details)
    if any(word in lower_msg for word in ["flat", "rent", "amount", "deposit", "notice", "maintenance"]):
        template = LOCAL_TEMPLATES["rent agreement"]
        details = extract_template_details(message)
        template = fill_template(template, details)
        return "NOTICE: High traffic detected. I've noted those details. Here is a **Local Template** filled with your information:\n\n" + template
            
    return "I'm sorry, I'm currently unable to connect to my AI brains due to heavy traffic. Please try again in 1-2 minutes, or check the 'Templates' section for manual drafts."

@app.route('/api/chat', methods=['POST'])
def chat():
    # Handle both JSON and Multipart (for file uploads)
    if request.content_type.startswith('multipart/form-data'):
        user_message = request.form.get('message', '')
        conversation_id = request.form.get('conversation_id', 'default')
        language = request.form.get('language', 'English')
        files_data = []
        
        uploaded_files = request.files.getlist('files')
        for f in uploaded_files:
            file_bytes = f.read()
            if f.content_type == 'application/pdf':
                # Extract text for PDF
                pdf_text = extract_text_from_pdf(io.BytesIO(file_bytes))
                user_message += f"\n\n[Content from Attached PDF ({f.filename})]:\n{pdf_text}"
            elif f.content_type.startswith('image/'):
                # Encode image for multimodal AI
                base64_image = base64.b64encode(file_bytes).decode('utf-8')
                files_data.append({
                    "type": f.content_type,
                    "data": base64_image,
                    "filename": f.filename
                })
    else:
        data = request.json
        user_message = data.get('message', '')
        conversation_id = data.get('conversation_id', 'default')
        language = data.get('language', 'English')
        files_data = None

    normalized_message = user_message.lower()

    if conversation_id not in conversations:
        conversations[conversation_id] = []

    history = conversations[conversation_id]

    try:
        # For simple keyword matches, we don't need AI or document analysis
        assistant_message = find_best_response(normalized_message) if not files_data else None

        if not assistant_message:
            assistant_message = get_ai_response(user_message, history, files_data, language)

        # Add to history
        conversations[conversation_id].append({"role": "user", "content": user_message})
        conversations[conversation_id].append({"role": "assistant", "content": assistant_message})
        save_conversations()

        return jsonify({
            'response': assistant_message,
            'conversation_id': conversation_id
        })

    except Exception as e:
        print(f"Chat error (falling back to local): {e}")
        # Even if a total system error occurs, avoid the 500 and give the user something useful
        return jsonify({
            'response': get_local_fallback_response(user_message),
            'conversation_id': conversation_id,
            'fallback': True
        })

@app.route('/api/reset', methods=['POST'])
def reset_conversation():
    data = request.json
    conversation_id = data.get('conversation_id', 'default')

    if conversation_id in conversations:
        conversations[conversation_id] = []
        save_conversations()

    return jsonify({'status': 'conversation reset'})

@app.route('/api/legal_categories')
def get_legal_categories():
    # Common legal categories in Indian law
    categories = [
        {"id": "constitutional", "name": "Constitutional Law"},
        {"id": "criminal", "name": "Criminal Law"},
        {"id": "civil", "name": "Civil Law"},
        {"id": "family", "name": "Family Law"},
        {"id": "property", "name": "Property Law"},
        {"id": "contract", "name": "Contract Law"},
        {"id": "corporate", "name": "Corporate Law"},
        {"id": "ip", "name": "Intellectual Property"},
        {"id": "labor", "name": "Labor Law"},
        {"id": "tax", "name": "Tax Law"},
        {"id": "consumer", "name": "Consumer Protection"}
    ]
    return jsonify(categories)

@app.route('/api/templates')
def get_templates():
    # Standard legal templates for drafting
    templates = [
        {"id": "rent_agreement", "name": "Rent Agreement", "icon": "🏠"},
        {"id": "power_of_attorney", "name": "Power of Attorney", "icon": "📜"},
        {"id": "legal_notice", "name": "Legal Notice", "icon": "✉️"},
        {"id": "leave_license", "name": "Leave & License Agreement", "icon": "🔑"}
    ]
    return jsonify(templates)

@app.route('/api/conversations')
def get_all_conversations():
    metadata = []
    for conv_id, messages in conversations.items():
        title = "New Conversation"
        if messages:
            # Find the first user message for the title
            for msg in messages:
                if msg['role'] == 'user':
                    title = msg['content'][:30] + ("..." if len(msg['content']) > 30 else "")
                    break
        metadata.append({
            'id': conv_id,
            'title': title
        })
    # Sort by ID (our IDs start with 'default-' followed by timestamp)
    # Extract timestamp for correct sorting
    def get_timestamp(cid):
        try:
            return int(cid.split('-')[1])
        except (IndexError, ValueError):
            return 0
            
    metadata.sort(key=lambda x: get_timestamp(x['id']), reverse=True)
    return jsonify(metadata)

@app.route('/api/conversation/<conv_id>')
def get_conversation_history(conv_id):
    if conv_id in conversations:
        return jsonify({
            'id': conv_id,
            'history': conversations[conv_id]
        })
    return jsonify({'error': 'Conversation not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
