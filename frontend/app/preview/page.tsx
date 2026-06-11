// frontend/app/preview/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Eye, 
  Sparkles, 
  Share2, 
  Languages, 
  Film, 
  MessageSquare, 
  Copy, 
  Check, 
  Tag, 
  Image as ImageIcon 
} from "lucide-react";

const API_BASE = "http://localhost:8000";

export default function PreviewPage() {
  const [selectedLang, setSelectedLang] = useState("Hindi");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [version, setVersion] = useState(1);
  
  const [campaignData, setCampaignData] = useState<any>({
    product: { name: "Organic Cardamom", price: 350.00 },
    keywords: {
      primary: ["organic cardamom", "kerala cardamom"],
      secondary: ["spices online", "elaichi pods"],
      long_tail: ["buy cardamom price online in kerala", "best organic green elaichi"],
      intent: ["order cardamom cash on delivery", "buy organic elaichi"],
      regional: ["kochi spices store", "munnar hill elaichi"]
    },
    script: {
      title: "Festive Spice Campaign",
      hook: "Is your tea missing that authentic kerala aroma? ☕",
      problem: "Most market cardamom is artificially colored, stale, and completely flavorless.",
      solution: "VyaparAI organic cardamom is handpicked in Idukki, vacuum sealed, and shipped fresh.",
      showcase: "100% natural cardamoms, rich in essential oils, green color, zero additives.",
      benefits: "Intense cardamon aroma, long shelf life, aids digestion, free shipping nationwide.",
      cta: "Reply now to get 10% off and free shipping on your first pack!",
      thumbnail_text: "Pure Elaichi!",
      thumbnail_prompt: "Cardamom pods overflowing from a clay bowl, dark rustic background, high resolution, macro photography"
    }
  });

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const languages = ["Hindi", "Tamil", "Telugu", "Malayalam"];

  const activeTranslations = {
    Hindi: {
      title: "उत्सव मसाला अभियान",
      hook: "क्या आपकी चाय में केरल की असली खुशबू गायब है? ☕",
      problem: "बाजार में मिलने वाली इलायची कृत्रिम रूप से रंगी हुई, बासी और बेस्वाद होती है।",
      solution: "व्यापारएआई जैविक इलायची इडुक्की में चुनी जाती है, वैक्यूम पैक करके भेजी जाती है।",
      cta: "अभी उत्तर दें और अपने पहले पैक पर 10% की छूट और मुफ्त डिलीवरी पाएं!"
    },
    Tamil: {
      title: "பண்டிகை மசாலா பிரச்சாரம்",
      hook: "உங்கள் தேநீரில் கேரளா ஏலக்காயின் நறுமணம் இல்லையா? ☕",
      problem: "சந்தையில் கிடைக்கும் பெரும்பாலான ஏலக்காய் நிறமூட்டப்பட்டது மற்றும் சுவையற்றது.",
      solution: "எங்கள் ஏலக்காய் இடுக்கியில் கைமுறையாக அறுவடை செய்யப்பட்டு புதியதாக அனுப்பப்படுகிறது.",
      cta: "இப்போதே பதிலளித்து, 10% தள்ளுபடி மற்றும் இலவச டெலிவரி பெறுங்கள்!"
    },
    Telugu: {
      title: "పండుగ మసాలా ప్రచారం",
      hook: "మీ టీలో కేరళ యాలకుల సువాసన లోపించిందా? ☕",
      problem: "మార్కెట్లో లభించే చాలా యాలకులు కృత్రిమ రంగులతో కూడి నిల్వ ఉన్నవిగా ఉంటాయి.",
      solution: "మా ఆర్గానిక్ యాలకులు ఇడుక్కి కొండల నుండి సేకరించబడి తాజాగా పంపిణీ చేయబడతాయి.",
      cta: "ఇప్పుడే సమాధానం ఇవ్వండి మరియు 10% తగ్గింపుతో పాటు ఉచిత డెలివరీ పొందండి!"
    },
    Malayalam: {
      title: "ആഘോഷ സുഗന്ധവ്യഞ്ജന കാമ്പയിൻ",
      hook: "നിങ്ങളുടെ ചായയിൽ യഥാർത്ഥ കേരള ഏലക്കായുടെ മണം കുറവാണോ? ☕",
      problem: "മാർക്കറ്റിൽ ലഭിക്കുന്ന ഏലക്കായ പലപ്പോഴും കൃത്രിമ നിറം ചേർത്തതും മണമില്ലാത്തതുമാണ്.",
      solution: "ഇടുക്കിയിലെ തോട്ടങ്ങളിൽ നിന്ന് നേരിട്ട് ശേഖരിച്ച ജൈവ ഏലക്കായ നിങ്ങളുടെ വീട്ടിലെത്തിക്കുന്നു.",
      cta: "ഇപ്പോൾ തന്നെ ഓർഡർ ചെയ്യൂ, 10% ഡിസ്കൗണ്ടും ഫ്രീ ഡെലിവറിയും സ്വന്തമാക്കൂ!"
    }
  };

  const activeText = activeTranslations[selectedLang as keyof typeof activeTranslations] || activeTranslations.Hindi;

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            Campaign Assets Review
          </h1>
          <p className="text-slate-400 mt-2">
            Audit structured copy hooks, thumbnail layout prompts, and keywords categorized by our agents.
          </p>
        </div>
        
        {/* Toggle details */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 gap-1">
            <button
              onClick={() => setVersion(1)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                version === 1 ? "bg-slate-800 text-white border border-slate-700" : "text-slate-500"
              }`}
            >
              V1 (QA: 85)
            </button>
            <button
              disabled
              className="px-3 py-1.5 rounded-lg text-xs font-bold text-slate-700"
            >
              V2 (Draft)
            </button>
          </div>

          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 gap-1">
            {languages.map(lang => (
              <button
                key={lang}
                onClick={() => setSelectedLang(lang)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                  selectedLang === lang ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Languages className="w-3.5 h-3.5" />
                {lang}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Expanded Keyword Groups */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-panel rounded-2xl p-6">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Tag className="w-5 h-5 text-indigo-400" />
              SEO Keywords Classification (KeywordAgent)
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Primary Keywords</span>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {campaignData.keywords.primary.map((kw: string) => (
                    <span key={kw} className="bg-slate-900 border border-slate-800 text-xs px-2.5 py-1 rounded-lg text-slate-300">#{kw}</span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Secondary Keywords</span>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {campaignData.keywords.secondary.map((kw: string) => (
                    <span key={kw} className="bg-slate-900 border border-slate-800 text-xs px-2.5 py-1 rounded-lg text-slate-300">#{kw}</span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Long Tail Keywords</span>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {campaignData.keywords.long_tail.map((kw: string) => (
                    <span key={kw} className="bg-slate-900 border border-slate-800 text-xs px-2.5 py-1 rounded-lg text-slate-300">#{kw}</span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Regional Keywords</span>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {campaignData.keywords.regional.map((kw: string) => (
                    <span key={kw} className="bg-slate-900 border border-slate-800 text-xs px-2.5 py-1 rounded-lg text-slate-300">#{kw}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Structured Script View */}
          <div className="glass-panel rounded-2xl p-6 space-y-6">
            <h3 className="text-lg font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
              <Film className="w-5 h-5 text-indigo-400" />
              Structured Screenplay Script ({selectedLang})
            </h3>

            <div className="space-y-4">
              {/* Hook */}
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest block mb-1">Hook (0-10 sec)</span>
                <p className="text-sm text-slate-200">{activeText.hook}</p>
              </div>

              {/* Problem */}
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                <span className="text-[10px] font-bold text-amber-400 uppercase tracking-widest block mb-1">Problem Bridge</span>
                <p className="text-sm text-slate-200">{activeText.problem}</p>
              </div>

              {/* Solution */}
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest block mb-1">Solution Showcase</span>
                <p className="text-sm text-slate-200">{activeText.solution}</p>
              </div>

              {/* CTA */}
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                <span className="text-[10px] font-bold text-purple-400 uppercase tracking-widest block mb-1">Call to Action</span>
                <p className="text-sm text-slate-200">{activeText.cta}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Thumbnail layouts and preview */}
        <div className="space-y-6">
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
              <ImageIcon className="w-5 h-5 text-indigo-400" />
              Clickable Thumbnail layout (ThumbnailAgent)
            </h3>
            
            <div className="space-y-3">
              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Text Overlay</span>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-white font-bold mt-1.5 uppercase">
                  "{campaignData.script.thumbnail_text}"
                </div>
              </div>

              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Image Model Prompt</span>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-slate-400 leading-relaxed mt-1.5 italic">
                  "{campaignData.script.thumbnail_prompt}"
                </div>
              </div>
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-6 text-center">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wide mb-4 text-left">Vertical Video Mock</h3>
            <div className="w-[200px] h-[350px] mx-auto rounded-2xl bg-slate-950 border-4 border-slate-900 flex flex-col justify-end p-4 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-indigo-950/20 to-transparent flex flex-col justify-end p-3 text-center space-y-2">
                <span className="text-[9px] bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded w-max mx-auto">Hindi Voiceover</span>
                <p className="text-[10px] text-slate-100 bg-slate-950/70 p-2 rounded-lg border border-slate-850 truncate">
                  {activeText.hook}
                </p>
              </div>
            </div>
            
            <Link href="/approval" className="w-full mt-6 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-xl block transition">
              Verify and Approve Campaign
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
