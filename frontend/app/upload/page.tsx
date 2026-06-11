// frontend/app/upload/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, Sparkles, Building2, Package, MapPin, CheckCircle2, Circle, Image as ImageIcon, Trash2 } from "lucide-react";

const API_BASE = "http://localhost:8000";

export default function UploadPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  // Form states
  const [businessName, setBusinessName] = useState("Kochi Spice Farm");
  const [location, setLocation] = useState("Kochi, Kerala");
  const [contact, setContact] = useState("+91 9447012345");
  const [industry, setIndustry] = useState("Spices & Agri");

  const [productName, setProductName] = useState("Organic Cardamom");
  const [description, setDescription] = useState("Handpicked fresh green cardamom sourced directly from the hills of Idukki.");
  const [price, setPrice] = useState("350");
  
  // Image file paths simulation
  const [images, setImages] = useState<string[]>([
    "/static/media/cardamom_close.jpg",
    "/static/media/cardamom_farm.jpg",
    "/static/media/cardamom_pack.jpg"
  ]);

  const pipelineSteps = [
    "Registering Business Profile...",
    "Uploading Product & Image catalog (3 assets logged)...",
    "Discovering core, intent, and regional keywords (KeywordAgent)...",
    "Auditing local SEO trend signals & topic boards (TrendAgent)...",
    "Drafting structured video script with hooks, problem & solution scene details (ScriptAgent & Llama 3.1)...",
    "Composing graphic layout blueprints and generative prompts (ThumbnailAgent)...",
    "Running automated script audit check & scoring scorecards (QualityAgent)...",
    "Stitching MP4 video clips with regional voiceovers (VideoAgent)...",
    "Registering YouTube publication hook (YouTubePublishingAgent)..."
  ];

  const handleAddMockImage = () => {
    if (images.length >= 10) return;
    const mockImgs = [
      "/static/media/spices_mix.jpg",
      "/static/media/cardamom_pods.jpg",
      "/static/media/packaging_box.jpg"
    ];
    const pick = mockImgs[Math.floor(Math.random() * mockImgs.length)];
    setImages(prev => [...prev, pick]);
  };

  const handleRemoveImage = (index: number) => {
    setImages(prev => prev.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (images.length < 3) {
      alert("Please upload at least 3 product images (maximum 10).");
      return;
    }
    setLoading(true);
    setCurrentStep(0);

    try {
      // Step 1: Create Business
      const bizRes = await fetch(`${API_BASE}/business`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: businessName,
          location: location,
          contact: contact,
          industry: industry
        })
      });
      const bizData = await bizRes.json();
      const bizId = bizData.data.id;
      
      setCurrentStep(1);

      // Step 2: Create Product
      const prodRes = await fetch(`${API_BASE}/product`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_id: bizId,
          name: productName,
          description: description,
          price: parseFloat(price),
          images: images
        })
      });
      const prodData = await prodRes.json();
      const prodId = prodData.data.id;

      setCurrentStep(2);

      // Trigger sequential steps timer for loader
      const interval = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= pipelineSteps.length - 1) {
            clearInterval(interval);
            return prev;
          }
          return prev + 1;
        });
      }, 2500);

      // Step 3: Run CrewAI campaign generator (8-agent)
      const crewRes = await fetch(`${API_BASE}/generate-content`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: prodId,
          location: "IN"
        })
      });
      
      clearInterval(interval);
      setCurrentStep(pipelineSteps.length);

      if (crewRes.ok) {
        router.push("/preview");
      } else {
        alert("Failed to execute 8-agent pipeline.");
      }
    } catch (err) {
      console.error(err);
      alert("An error occurred during workflow execution.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
          Create AI Marketing Campaign
        </h1>
        <p className="text-slate-400 mt-2">
          Submit product specs and visuals to trigger the 8-agent marketing crew automation.
        </p>
      </div>

      {!loading ? (
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Business details panel */}
          <div className="glass-panel rounded-2xl p-6 space-y-6">
            <h3 className="text-xl font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-4">
              <Building2 className="w-5 h-5 text-indigo-400" />
              Business Profile
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-2">Business Name</label>
                <input
                  type="text"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 transition"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-2">Location</label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 transition"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-300 mb-2">Industry</label>
                  <input
                    type="text"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 transition"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-300 mb-2">Contact</label>
                  <input
                    type="text"
                    value={contact}
                    onChange={(e) => setContact(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 transition"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Product and visuals panel */}
          <div className="glass-panel rounded-2xl p-6 space-y-6">
            <h3 className="text-xl font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-4">
              <Package className="w-5 h-5 text-indigo-400" />
              Product Details
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-2">Product Name</label>
                <input
                  type="text"
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 transition"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-2">Price (INR)</label>
                <input
                  type="number"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 transition"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-2">Product Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 transition"
                  required
                />
              </div>
            </div>
          </div>

          {/* Image Upload Area */}
          <div className="md:col-span-2 glass-panel rounded-2xl p-6 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
              <ImageIcon className="w-5 h-5 text-indigo-400" />
              Upload Product Images (3-10 assets)
            </h3>
            
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {images.map((img, idx) => (
                <div key={idx} className="relative aspect-video rounded-xl overflow-hidden bg-slate-900 border border-slate-800 flex items-center justify-center text-xs text-indigo-300 font-semibold p-2">
                  <span className="truncate">{img.split("/").pop()}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveImage(idx)}
                    className="absolute top-1 right-1 p-1 rounded-md bg-rose-500/20 text-rose-400 border border-rose-500/20 hover:bg-rose-500 hover:text-white transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              
              {images.length < 10 && (
                <button
                  type="button"
                  onClick={handleAddMockImage}
                  className="aspect-video rounded-xl bg-slate-900/40 border border-dashed border-slate-800 hover:border-indigo-500/40 hover:bg-slate-900/80 transition flex flex-col items-center justify-center gap-1 text-xs text-slate-500 hover:text-indigo-400"
                >
                  <Upload className="w-5 h-5" />
                  Add Image
                </button>
              )}
            </div>
          </div>

          <div className="md:col-span-2 flex justify-end">
            <button
              type="submit"
              className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold px-8 py-4 rounded-xl shadow-xl transition"
            >
              <Sparkles className="w-5 h-5" />
              Deploy VyaparAI Crew
            </button>
          </div>
        </form>
      ) : (
        /* Expanded pipeline tracking overlay */
        <div className="glass-panel rounded-2xl p-8 max-w-2xl mx-auto space-y-6">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-full border-4 border-t-indigo-500 border-r-transparent border-slate-800 animate-spin mx-auto mb-4" />
            <h3 className="text-2xl font-bold text-white">Deploying Multi-Agent System</h3>
            <p className="text-slate-400 text-sm">Evaluating quality rules and publishing triggers...</p>
          </div>

          <div className="space-y-3.5 border-t border-slate-800 pt-6">
            {pipelineSteps.map((step, idx) => (
              <div key={idx} className="flex items-start gap-3 text-xs leading-relaxed">
                {currentStep > idx ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                ) : currentStep === idx ? (
                  <div className="w-4 h-4 rounded-full border-2 border-t-indigo-400 border-slate-700 animate-spin flex-shrink-0" />
                ) : (
                  <Circle className="w-4 h-4 text-slate-700 flex-shrink-0" />
                )}
                <span className={currentStep === idx ? "text-indigo-300 font-semibold" : currentStep > idx ? "text-slate-400" : "text-slate-600"}>
                  {step}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
