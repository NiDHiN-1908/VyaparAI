# backend/models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class BusinessCreate(BaseModel):
    name: str = Field(..., example="Ravi Organics")
    location: str = Field(..., example="Kochi, Kerala")
    contact: Optional[str] = Field(None, example="+91 9876543210")
    industry: Optional[str] = Field(None, example="Agriculture")

class ProductCreate(BaseModel):
    business_id: str
    name: str = Field(..., example="Virgin Coconut Oil")
    description: str = Field(..., example="100% natural cold pressed coconut oil.")
    price: float = Field(..., gt=0, example=299.00)
    image_url: Optional[str] = Field(None, example="/static/media/coconut_oil.jpg")

class GenerateContentRequest(BaseModel):
    product_id: str
    location: str = Field("IN", example="IN")

class TranslateRequest(BaseModel):
    script_id: str
    language: str = Field(..., example="Hindi") # Malayalam, Tamil, Hindi, Telugu

class GenerateVideoRequest(BaseModel):
    voiceover_id: str
    image_path: Optional[str] = None

class ApproveRequest(BaseModel):
    video_id: str
    status: str = Field(..., example="approved") # approved, rejected, revision_requested

class CommentCreateRequest(BaseModel):
    video_id: str
    username: str = Field(..., example="anil_kumar")
    comment_text: str = Field(..., example="What is the price of this oil?")

class LeadCreateRequest(BaseModel):
    business_id: str
    username: str
    intent: Optional[str] = "MEDIUM_INTENT"

class ChatRequest(BaseModel):
    lead_id: str
    product_id: str
    message: str = Field(..., example="I want to buy this. Can you help me?")

class PaymentRequest(BaseModel):
    order_id: str
    status: str = Field(..., example="paid") # paid, failed
    transaction_id: Optional[str] = None

class RegenerateRequest(BaseModel):
    product_id: str
    feedback: Optional[str] = Field(None, example="Change hook style and keywords density")
    location: str = Field("IN", example="IN")

class PublishRequest(BaseModel):
    video_id: str
