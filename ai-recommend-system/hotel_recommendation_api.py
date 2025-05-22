import os
import json
import torch
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from improved_recommendation import ImprovedLearningRecommender
import traceback

app = Flask(__name__)
CORS(app)  # Cross-Origin isteklerine izin ver

# Global değişkenler
users_file = 'datas/expanded_users.json'
hotels_file = 'datas/expanded_hotels.json'
model_path = "improved_hotel_recommender_model.pth"

# Eğer genişletilmiş veri seti yoksa, orijinal veri setini kullan
if not os.path.exists(users_file):
    users_file = 'datas/mock_users.json'
if not os.path.exists(hotels_file):
    hotels_file = 'datas/mock_nevsehir_hotels.json'

print(f"Kullanılan veri setleri: {users_file}, {hotels_file}")

try:
    # İlk deneme - mevcut modeli yüklemeye çalış
    recommender = ImprovedLearningRecommender(users_file, hotels_file, model_path)
    print("Derin öğrenme modeli başarıyla yüklendi.")
except Exception as e:
    if "size mismatch" in str(e):
        print(f"Model boyutu uyumsuzluğu tespit edildi: {e}")
        print("Eski model dosyasını yedekliyorum ve yeni model eğitiyorum...")
        
        # Eski model dosyasını yedekle
        if os.path.exists(model_path):
            backup_path = f"{model_path}.backup"
            try:
                os.rename(model_path, backup_path)
                print(f"Eski model {backup_path} olarak yedeklendi.")
            except Exception as rename_error:
                print(f"Yedekleme hatası: {rename_error}")
        
        # Yeni model eğit
        try:
            print("Yeni derin öğrenme modeli eğitiliyor...")
            recommender = ImprovedLearningRecommender(users_file, hotels_file)
            recommender.train(evaluate=True)
            print("Yeni model başarıyla eğitildi ve kaydedildi.")
        except Exception as train_error:
            print(f"Model eğitimi hatası: {train_error}")
            raise
    else:
        print(f"Beklenmeyen hata: {e}")
        raise

@app.route('/api/recommend', methods=['POST'])
def recommend():
    """
    Kullanıcı bilgilerine göre otel önerileri döndüren API endpoint'i - Derin öğrenme modeli kullanan versiyon
    
    Request body örneği:
    {
        "user_id": 1,  // Varolan bir kullanıcı ID'si
        "top_n": 5     // Kaç adet öneri isteniyor (opsiyonel, default 5)
    }
    
    veya yeni kullanıcı için:
    {
        "user": {
            "name": "Deneme Kullanıcı",
            "preferredBudget": {"min": 1000, "max": 1500},
            "preferredRoomType": "STANDARD",
            "requiredCapacity": 2,
            "preferredAmenities": ["WiFi", "TV"]
        },
        "top_n": 3
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "Geçersiz JSON verisi"}), 400
            
        # Kullanıcı ID ile öneri alma (yapay zeka modeli ile)
        if "user_id" in data:
            user_id = data.get("user_id")
            top_n = data.get("top_n", 5)
            debug = data.get("debug", False)
            
            # Derin öğrenme modeli ile öneriler al
            recommendations = recommender.recommend_hotels(user_id, top_n=top_n, debug=debug)
            
            # Öneriler için detaylı açıklamalar ekle
            for rec in recommendations:
                explanation = recommender.explain_recommendation(user_id, rec['hotel_id'])
                if explanation and "error" not in explanation:
                    rec['detailed_explanation'] = explanation
            
            return jsonify({
                "user_id": user_id,
                "ai_powered": True,
                "recommendations": recommendations
            })
            
        # Yeni kullanıcı bilgileriyle öneri alma (yeni yaklaşım gerekli)
        elif "user" in data:
            user_data = data.get("user")
            top_n = data.get("top_n", 5)
            
            # Kullanıcı verilerinin doğruluğunu kontrol et
            required_fields = ["preferredBudget", "preferredRoomType", "requiredCapacity", "preferredAmenities"]
            for field in required_fields:
                if field not in user_data:
                    return jsonify({"error": f"Eksik alan: {field}"}), 400
            
            # Geçici kullanıcı oluştur, önerileri al ve sonra kullanıcıyı sil
            temp_user_id = create_temporary_user(user_data)
            
            try:
                # Yeni kullanıcı için öneriler al
                recommendations = recommender.recommend_hotels(temp_user_id, top_n=top_n)
                
                # Öneriler için detaylı açıklamalar ekle
                for rec in recommendations:
                    explanation = recommender.explain_recommendation(temp_user_id, rec['hotel_id'])
                    if explanation and "error" not in explanation:
                        rec['detailed_explanation'] = explanation
                
                # Yanıt döndür
                return jsonify({
                    "ai_powered": True,
                    "recommendations": recommendations
                })
            finally:
                # Her durumda geçici kullanıcıyı sil
                remove_temporary_user(temp_user_id)
        
        else:
            return jsonify({"error": "Geçersiz istek formatı. 'user_id' veya 'user' alanı gerekli"}), 400
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def create_temporary_user(user_data):
    """
    Yeni kullanıcı için geçici bir kullanıcı kaydı oluştur
    """
    try:
        # Kullanıcı listesini yükle
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        # Yeni benzersiz ID oluştur (mevcut en büyük ID + 1000)
        max_id = max(user.get('id', 0) for user in users)
        new_user_id = max_id + 1000
        
        # Yeni kullanıcı verisi
        new_user = {
            "id": new_user_id,
            "name": user_data.get("name", "Geçici Kullanıcı"),
            "email": f"temp_{new_user_id}@example.com",
            "age": user_data.get("age", 30),
            "gender": user_data.get("gender", "UNSPECIFIED"),
            "preferredBudget": user_data["preferredBudget"],
            "preferredRoomType": user_data["preferredRoomType"],
            "requiredCapacity": user_data["requiredCapacity"],
            "preferredAmenities": user_data["preferredAmenities"],
            "specialRequests": user_data.get("specialRequests", ""),
            "travelDates": user_data.get("travelDates", {"start": "", "end": ""})
        }
        
        # Yeni kullanıcıyı listeye ekle
        users.append(new_user)
        
        # Dosyaya kaydet
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        
        # Öneri sistemini yeniden başlat (kullanıcı sayısı değişti)
        global recommender
        recommender = ImprovedLearningRecommender(users_file, hotels_file, model_path)
        
        return new_user_id
    except Exception as e:
        print(f"Geçici kullanıcı oluşturma hatası: {e}")
        traceback.print_exc()
        raise

def remove_temporary_user(user_id):
    """
    Geçici kullanıcıyı sil
    """
    try:
        # Kullanıcı listesini yükle
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        # Kullanıcıyı filtrele
        users = [user for user in users if user.get('id') != user_id]
        
        # Dosyaya kaydet
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        
        # Not: Öneri sistemini şu anda güncellemeye gerek yok 
        # çünkü bu noktada öneriler zaten elde edildi
        
        return True
    except Exception as e:
        print(f"Geçici kullanıcı silme hatası: {e}")
        return False

@app.route('/api/users', methods=['GET'])
def get_users():
    """
    Mevcut kullanıcıları listeler (sadece ID ve isim bilgileri)
    """
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        # Geçici kullanıcıları filtrele (ID > 1000)
        filtered_users = [user for user in users if user.get('id', 0) < 1000]
        
        user_list = [{"id": user["id"], "name": user["name"]} for user in filtered_users]
        return jsonify(user_list)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Belirli bir kullanıcının detaylarını döndürür
    """
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        user = next((user for user in users if user['id'] == user_id), None)
        
        if user:
            return jsonify(user)
        else:
            return jsonify({"error": "Kullanıcı bulunamadı"}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 