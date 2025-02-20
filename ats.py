import openai
import streamlit as st
from PyPDF2 import PdfReader
import asyncio
import edge_tts
import sounddevice as sd
import soundfile as sf
import numpy as np
import os
from pydub import AudioSegment
from pydub.playback import play
import re

# OpenAI API key (keep it secure)
openai.api_key = "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"

class ATSAnalyzer:
    @staticmethod
    def get_openai_response(input_prompt, pdf_text, job_description):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a highly skilled ATS analyzer."},
                    {"role": "user", "content": input_prompt},
                    {"role": "user", "content": pdf_text},
                    {"role": "user", "content": job_description}
                ]
            )
            return response.choices[0].message['content']
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            return None

    @staticmethod
    def extract_text_from_pdf(uploaded_file):
        try:
            pdf_reader = PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            st.error(f"Error extracting PDF text: {str(e)}")
            return None

async def səsləndir(mətn):
    mp3_fayli = "cavab3.mp3"
    kommunikator = edge_tts.Communicate(mətn, voice="az-AZ-BabekNeural")
    await kommunikator.save(mp3_fayli)

    # Audio faylını oxuyub sürəti artırırıq
    audio = AudioSegment.from_mp3(mp3_fayli)
    sürətli_audio = audio.speedup(playback_speed=1.1)

    # Səsləndiririk
    play(sürətli_audio)
    os.remove(mp3_fayli)  # Səs faylını silirik

def ses_yazma(dosya_adi, muddet=10, fs=48000, bit_depth='int16'):
    st.write("Dinlənilir...")

    # Səs yazmaq üçün mikrofonu istifadə edirik
    audio = sd.rec(int(muddet * fs), samplerate=fs, channels=1, dtype=bit_depth)
    sd.wait()  # Yazma bitənə qədər gözləyir

    # Səs faylını yazırıq
    sf.write(dosya_adi, audio, fs)
    st.write("Dinləmə tamamlandı.")

def sesten_mətnə(dosya_adi):
    st.write("Mətnə çevrilir...")
    with open(dosya_adi, "rb") as audio_file:
        response = openai.Audio.transcribe("whisper-1", audio_file, language="az")
    return response["text"]

def qrammatik_duzeltme(metin):
    prompt = f"""
    Aşağıdakı mətni Azərbaycan dilinin qrammatik qaydalarına tam uyğun olaraq düzəlt. 
    Mətnin məzmununa və mənasına heç bir müdaxilə etmə, yalnız qrammatik səhvləri düzəlt.
    Mətn: "{metin}"
    Yalnız düzəldilmiş mətni yaz, əlavə izah vermə.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Sən Azərbaycan dilinin qrammatikasına uyğun olaraq mətnləri düzəldən bir dil redaktorusan."},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content'].strip()

def gpt_sual_hazirla(cavab):
    prompt = f"""
    Verilən cavabı dərindən təhlil et və yalnız 1 konkret sual hazırla. Bu sual aşağıdakı kriteriyalara əsaslanmalıdır:

    1. İstifadəçinin şəxsi təcrübələrini nəzərdən keçir.
    2. Bu təcrübələrin müvafiq vakansiya tələbləri ilə uyğunluğunu qiymətləndir.
    3. Təcrübələrə əsaslanaraq daha dərindən bir sual ver, amma bu sual vakansiyanın bacarıq və təcrübə tələblərinə uyğun olmalıdır.

    Sual hazırlayarkən, Azərbaycan dilində düzgün qrammatika qaydalarına riayət et və heç bir qrammatik səhv etmə. Sual insan tərzində olmalı və heç bir izah, şərh və ya əlavə mətn daxil etmə.

    Cavab: {cavab}

    Vakansiya tələbləri:
    - Əlaqəli sahə üzrə ali təhsil (İqtisadiyyat, Marketinq, Tətbiqi Riyaziyyat və ya digər);
    - Data analitika, məlumatların təhlili və işlənməsi üzrə əsas biliklər;
    - Data analitika üzrə minimum 1 il təcrübə;
    - Vizuallaşdırma alətlərindən istifadə təcrübəsi (Tableau, QlikView, PowerBI);
    - Excel bilikləri;
    - SQL kodlaşdırma dilləri üzrə əsas bacarıqlar;
    - Python və ya R kimi məlumatların təhlili və hesabatında geniş istifadə olunan proqramlaşdırma üzrə biliklər.

    Sualın strukturu:
    - Suallar yalnız istifadəçinin təcrübəsini daha da dərindən anlamağa yönəlməlidir.
    - Sual texniki və nəzəri bacarıqları yoxlamalıdır.
    - Qrammatika və dil qaydalarına tam riayət edərək sual verilməlidir.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Sən bir müsahibəçisən, vakansiya tələblərinə əsaslanaraq dərinləşdirilmiş suallar verirsən."},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content'].strip()

def main():
    # Page setup
    st.set_page_config(
        page_title="ATS Resume Expert",
        page_icon="📄",
        layout="wide"
    )

    # Main content
    st.markdown("""
    <div style="display: flex; justify-content: flex-start; margin-left: 0px; width: 800px; height: 450px; background-color: #000; border: 2px solid #ccc; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px;">
        Video Frame
    </div>
    """, unsafe_allow_html=True)


    # Sağ sidebar yaratmaq
    st.markdown("""
        <style>
            .sidebar-container {
                position: fixed;
                right: 0;
                top: 0;
                width: 350px;
                height: 100%;
                background-color: #f5f5f5;
                padding: 10px;
                box-shadow: -2px 0 5px rgba(0,0,0,0.1);
            }
        </style>
        <div class="sidebar-container">
            <p style="text-align: center;">🔍</p>
            <p style="font-size: 45px; text-align: center;">Vakansiyalar</p>
        </div>
        """, unsafe_allow_html=True)




    # CV upload and Interview section below the video
    st.subheader("Müsahibə başlaması üçün CV-nizi daxil edin")

    # Sidebar configuration for CV and job description
    st.sidebar.title("📄 ATS CV Analizi")
    job_description = st.sidebar.text_area("Vakansiya Tələbləri", height=200)
    uploaded_file = st.sidebar.file_uploader("CV Yüklə", type=["pdf"])

    # Only proceed if the file is uploaded and the job description is provided
    if uploaded_file and job_description:
        if st.sidebar.button("CV Analiz Et"):
            st.sidebar.markdown("Çalışır...")

            # Extract text from PDF
            pdf_text = ATSAnalyzer.extract_text_from_pdf(uploaded_file)

            if pdf_text:
                prompt = """
                    As an ATS (Applicant Tracking System) expert, provide:
                    1. Overall match percentage (%)
                    2. Important missing keywords
                    3. Specific recommendations for improvement
                    Start with the percentage match prominently displayed.
                """

                # Get the OpenAI response
                response = ATSAnalyzer.get_openai_response(prompt, pdf_text, job_description)

                if response:
                    st.sidebar.write(response)

                    # Extract match percentage from the response
                    match_percentage = re.search(r"(\d+)%", response)
                    if match_percentage:
                        st.sidebar.markdown(f"### Match Percentage: {match_percentage.group(1)}%")

                        # Proceed with interview if match percentage is over 60%
                        if int(match_percentage.group(1)) > 60:
                            st.session_state.interview_active = True  # Set flag for interview system activation
                            st.write("CV uyğunluq faizi 60%-dən yuxarıdır. Müsahibəyə başlamağa hazırsınız!")
                        else:
                            st.session_state.interview_active = False  # Ensure interview system is inactive
                            st.write("CV uyğunluq faizi 60%-dən aşağıdır. Müsahibəyə başlamaq mümkün deyil.")
            else:
                st.error("CV-dən mətn çıxarıla bilmədi.")
    else:
        st.sidebar.info("Zəhmət olmasa məlumatları doğru daxil edin!")

    # Main page logic (only show interview if interview_active is True)
    if 'interview_active' in st.session_state and st.session_state.interview_active:
        st.write("Müsahibəyə başlamağa hazırsınız!")
        if st.button("Müsahibəyə Başla"):
            # Start voice interview process
            ilk_sual = "Təcrübəniz haqqında qısa məlumat verin!"
            asyncio.run(səsləndir(ilk_sual))

            # Record answer and convert to text
            ses_yazma("cavab.wav", muddet=15)
            cavab = sesten_mətnə("cavab.wav")
            st.write("Orijinal Cavab: " + cavab)

            # Grammar correction
            duzeltilmis_cavab = qrammatik_duzeltme(cavab)
            st.write("Düzəldilmiş Cavab: " + duzeltilmis_cavab)

            # Generate follow-up question
            yeni_sual = gpt_sual_hazirla(duzeltilmis_cavab)
            st.write("Yeni Sual: " + yeni_sual)

            # Ask the next question via TTS
            asyncio.run(səsləndir(yeni_sual))

if __name__ == "__main__":
    main()
