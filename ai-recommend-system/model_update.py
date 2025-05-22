import os
import torch
import shutil
from improved_recommendation import ImprovedLearningRecommender

def main():
    print("Öneri Sistemi Model Güncelleme Aracı")
    print("="*60)
    
    model_path = "improved_hotel_recommender_model.pth"
    backup_path = f"{model_path}.backup"
    users_file = 'datas/expanded_users.json'
    hotels_file = 'datas/expanded_hotels.json'
    
    # Önce mevcut modeli silmeye çalış
    if os.path.exists(model_path):
        try:
            # Yedek dosyası varsa önce onu silmeye çalış
            if os.path.exists(backup_path):
                os.remove(backup_path)
                print(f"Eski yedek dosyası silindi: {backup_path}")
            
            # Şimdi mevcut modeli yedekleyelim
            shutil.copy2(model_path, backup_path)
            print(f"Mevcut model yedeklendi: {backup_path}")
            
            # Ana model dosyasını sil
            os.remove(model_path)
            print(f"Mevcut model dosyası silindi: {model_path}")
        except Exception as e:
            print(f"Dosya işlemleri sırasında hata: {e}")
    else:
        print("Mevcut model dosyası bulunamadı. Yeni model eğitilecek.")
    
    # Yeni model eğit
    print("\nYeni model eğitiliyor...")
    try:
        # ImprovedLearningRecommender nesnesi model_path olmadan oluşturulur
        # böylece model yüklemeye çalışılmaz
        recommender = ImprovedLearningRecommender(users_file, hotels_file)
        
        # Modeli eğit
        recommender.train(evaluate=True)
        
        print("\nModel eğitimi tamamlandı.")
        print(f"Yeni model {model_path} olarak kaydedildi.")
        
        # Örnekleme yap
        print("\nÖrnek öneriler oluşturuluyor...")
        test_user_ids = [1, 2, 3]  # Örnek kullanıcılar
        
        for user_id in test_user_ids:
            print(f"\n{'='*80}")
            print(f"Kullanıcı ID: {user_id} için öneriler:")
            
            recommendations = recommender.recommend_hotels(user_id, top_n=3, debug=True)
            
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. {rec['hotel_name']} - {rec['room_name']}")
                print(f"   Tahmini Puan: {rec['predicted_rating']}")
                print(f"   Oda Tipi: {rec['room_type']}")
                print(f"   Fiyat: {rec['price']} TL")
                print(f"   Öneri Açıklaması: {rec['recommendation_type']}")
                
                # Her öneri için detaylı açıklamayı göster
                explanation = recommender.explain_recommendation(user_id, rec['hotel_id'])
                if explanation and "error" not in explanation:
                    print(f"\n   Detaylı Açıklama: {explanation['explanation']}")
        
        print("\nİşlem tamamlandı. Artık model_evaluation.py scriptini çalıştırabilirsiniz.")
        return True
    except Exception as e:
        print(f"Model eğitimi sırasında hata oluştu: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main() 