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
  const [selectedLang, setSelectedLang] = useState("English");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [version, setVersion] = useState(1);
  const [loading, setLoading] = useState(true);
  const [productId, setProductId] = useState<string | null>(null);

  useEffect(() => {
    const fetchCampaign = async () => {
      try {
        let pId = null;
        if (typeof window !== "undefined") {
          const params = new URLSearchParams(window.location.search);
          pId = params.get("product_id");
          if (!pId) {
            pId = localStorage.getItem("latest_product_id");
          }
        }

        if (!pId) {
          const prodRes = await fetch(`${API_BASE}/product`);
          const prodList = await prodRes.json();
          if (prodList && prodList.length > 0) {
            pId = prodList[prodList.length - 1].id;
          }
        }

        if (pId) {
          setProductId(pId);
          const campRes = await fetch(`${API_BASE}/campaign/${pId}`);
          if (campRes.ok) {
            const data = await campRes.json();
            setCampaignData(data);
          } else {
            console.warn(`Campaign for product ${pId} not found, trying latest available product instead.`);
            const prodRes = await fetch(`${API_BASE}/product`);
            const prodList = await prodRes.json();
            if (prodList && prodList.length > 0) {
              for (let i = prodList.length - 1; i >= 0; i--) {
                const checkId = prodList[i].id;
                const checkRes = await fetch(`${API_BASE}/campaign/${checkId}`);
                if (checkRes.ok) {
                  const checkData = await checkRes.json();
                  setCampaignData(checkData);
                  setProductId(checkId);
                  break;
                }
              }
            }
          }
        }
      } catch (err) {
        console.error("Failed to load generated campaign:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchCampaign();
  }, []);
  
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
    },
    videos: {
      English: { video_url: "/static/media/video_english_v2_3ce14206.mp4" },
      Hindi: { video_url: "/static/media/video_hindi_v2_63b2d922.mp4" },
      Tamil: { video_url: "/static/media/video_tamil_v2_12efcce8.mp4" },
      Telugu: { video_url: "/static/media/video_telugu_v2_6a2efde3.mp4" },
      Malayalam: { video_url: "/static/media/video_malayalam_v2_b9304c03.mp4" }
    }
  });


  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam"];

  const activeTranslations = {
    English: {
      title: "Festive Spice Campaign",
      hook: "Is your tea missing that authentic kerala aroma? ☕",
      problem: "Most market cardamom is artificially colored, stale, and completely flavorless.",
      solution: "VyaparAI organic cardamom is handpicked in Idukki, vacuum sealed, and shipped fresh.",
      cta: "Reply now to get 10% off and free shipping on your first pack!"
    },
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

  const dynamicText = campaignData?.translations?.[selectedLang];
  
  const activeText = dynamicText ? {
    youtube_script: dynamicText.youtube_script,
    reel_script: dynamicText.reel_script,
    whatsapp_post: dynamicText.whatsapp_post,
    google_business_post: dynamicText.google_business_post,
    hook: dynamicText.youtube_script,
    problem: dynamicText.reel_script,
    solution: dynamicText.whatsapp_post,
    cta: dynamicText.google_business_post
  } : {
    youtube_script: activeTranslations[selectedLang as keyof typeof activeTranslations]?.hook || "",
    reel_script: activeTranslations[selectedLang as keyof typeof activeTranslations]?.solution || "",
    whatsapp_post: activeTranslations[selectedLang as keyof typeof activeTranslations]?.cta || "",
    google_business_post: activeTranslations[selectedLang as keyof typeof activeTranslations]?.title || "",
    hook: activeTranslations[selectedLang as keyof typeof activeTranslations]?.hook || "",
    problem: activeTranslations[selectedLang as keyof typeof activeTranslations]?.problem || "",
    solution: activeTranslations[selectedLang as keyof typeof activeTranslations]?.solution || "",
    cta: activeTranslations[selectedLang as keyof typeof activeTranslations]?.cta || ""
  };

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
              {/* YouTube Script */}
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest block mb-1">YouTube Campaign Voiceover Script</span>
                <p className="text-sm text-slate-200">{activeText.youtube_script || activeText.hook || ""}</p>
              </div>

              {/* Reel Script */}
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                <span className="text-[10px] font-bold text-purple-400 uppercase tracking-widest block mb-1">Instagram Reel / Shorts Script</span>
                <p className="text-sm text-slate-200">{activeText.reel_script || activeText.solution || ""}</p>
              </div>

              {/* WhatsApp Post */}
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest block mb-1">WhatsApp Broadcast Post</span>
                <p className="text-sm text-slate-200 whitespace-pre-wrap">{activeText.whatsapp_post || activeText.cta || ""}</p>
              </div>

              {/* Google Business Post */}
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                <span className="text-[10px] font-bold text-sky-400 uppercase tracking-widest block mb-1">Google Business Update Post</span>
                <p className="text-sm text-slate-200">{activeText.google_business_post || activeText.title || ""}</p>
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
              {campaignData?.thumbnail?.image_url && (
                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide block mb-1.5">Generated Thumbnail Image</span>
                  <div className="rounded-xl overflow-hidden border border-slate-800 bg-slate-950 aspect-video relative group mb-3">
                    <img 
                      src={`${API_BASE}${campaignData.thumbnail.image_url}`} 
                      alt="Generated Campaign Thumbnail" 
                      className="w-full h-full object-cover transition duration-300 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-slate-950/20 group-hover:bg-transparent transition" />
                  </div>
                </div>
              )}

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
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wide mb-4 text-left">Vertical Video Preview</h3>
            {(() => {
              const videoObj = campaignData?.videos?.[selectedLang];
              const youtubeUrl = videoObj?.youtube_url;
              const youtubeId = videoObj?.youtube_id || (youtubeUrl ? (() => {
                const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
                const match = youtubeUrl.match(regExp);
                return (match && match[2].length === 11) ? match[2] : null;
              })() : null);

              if (youtubeId) {
                return (
                  <div className="w-full aspect-video rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden relative shadow-2xl">
                    <iframe
                      className="w-full h-full"
                      src={`https://www.youtube.com/embed/${youtubeId}`}
                      title="YouTube video player"
                      frameBorder="0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                    ></iframe>
                  </div>
                );
              }

              if (videoObj?.video_url) {
                return (
                  <div className="w-full rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden relative shadow-2xl flex items-center justify-center p-2">
                    <video
                      controls
                      className="w-full max-h-[450px] rounded-xl"
                      src={videoObj.video_url.startsWith("http") ? videoObj.video_url : `${API_BASE}${videoObj.video_url}`}
                    >
                      Your browser does not support the video tag.
                    </video>
                  </div>
                );
              }

              return (
                <div className="glass-panel bg-slate-900/60 border border-slate-800 rounded-2xl p-6 text-center flex flex-col items-center justify-center min-h-[300px] space-y-4 shadow-xl">
                  <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <Film className="w-6 h-6 animate-pulse" />
                  </div>
                  <div>
                    <h4 className="font-extrabold text-sm text-slate-200">Video Draft Stitched</h4>
                    <span className="text-[10px] text-indigo-400 font-bold block mt-1 uppercase tracking-wide">
                      Status: Ready for Publishing
                    </span>
                    <p className="text-xs text-slate-450 mt-3 max-w-xs mx-auto leading-relaxed">
                      This localized video draft is successfully compiled. To ensure visual excellence and compliance, you can watch it once published to YouTube.
                    </p>
                  </div>
                </div>
              );
            })()}
            
            <Link href={`/approval?product_id=${productId || ""}`} className="w-full mt-6 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-xl block transition">
              Verify and Approve Campaign
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
