import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import json
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
import os
import random
import time
from typing import List, Dict, Tuple, Any
from tqdm import tqdm

# GPU kullanılabilirliğini kontrol et
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Kullanılan cihaz: {device}")

# İyileştirilmiş derin öğrenme temelli öneri sistemi için sabit değerler
EMBEDDING_DIM = 64  # Embedding vektörlerinin boyutu
HIDDEN_LAYERS = [128, 64, 32]  # Gizli katmanların boyutları
LEARNING_RATE = 0.0005  # Öğrenme oranı
BATCH_SIZE = 32  # Batch boyutu
NUM_EPOCHS = 100  # Epoch sayısı
EARLY_STOPPING_PATIENCE = 15  # Erken durdurma sabırsızlık sınırı

class ImprovedHotelDataset(Dataset):
    """Otel ve kullanıcı verilerini işleyen geliştirilmiş PyTorch Dataset sınıfı"""
    
    def __init__(self, users_file: str, hotels_file: str, synthesize_ratings: bool = True):
        """
        Veri kümesini başlatır ve önişleme yapar.
        
        Args:
            users_file: Kullanıcı verileri JSON dosyasının yolu
            hotels_file: Otel verileri JSON dosyasının yolu
            synthesize_ratings: Eğitim için sentetik puanlama üretilip üretilmeyeceği
        """
        print(f"Veri dosyaları yükleniyor: {users_file}, {hotels_file}")
        start_time = time.time()
        
        # Veriyi yükle
        with open(users_file, 'r', encoding='utf-8') as f:
            self.users = json.load(f)
            
        with open(hotels_file, 'r', encoding='utf-8') as f:
            self.hotels = json.load(f)
            
        # Dosya yollarını sakla (diğer metodlar için)
        self.users_file = users_file
        self.hotels_file = hotels_file
            
        # ID'den indekse eşleme sözlükleri - Önce bunları oluştur
        self.user_ids = [user['id'] for user in self.users]
        self.hotel_ids = [hotel['id'] for hotel in self.hotels]
        
        self.user_id_to_index = {user_id: idx for idx, user_id in enumerate(self.user_ids)}
        self.hotel_id_to_index = {hotel_id: idx for idx, hotel_id in enumerate(self.hotel_ids)}
            
        # Kullanıcı ve otel özelliklerini çıkar
        self.user_features, _ = self._extract_user_features()
        self.hotel_features, _ = self._extract_hotel_features()
        
        # Özellik boyutları
        self.num_user_features = self.user_features.shape[1]
        self.num_hotel_features = self.hotel_features.shape[1]
        self.num_users = len(self.user_ids)
        self.num_hotels = len(self.hotel_ids)
        
        print(f"Veri yükleme tamamlandı. Kullanıcı sayısı: {self.num_users}, Otel sayısı: {self.num_hotels}")
        print(f"Kullanıcı özellik boyutu: {self.num_user_features}, Otel özellik boyutu: {self.num_hotel_features}")
        
        # Sentetik etkileşim/puanlama verileri oluştur
        if synthesize_ratings:
            self.interactions = self._synthesize_interactions()
            self.X_train, self.X_test, self.y_train, self.y_test = self._prepare_training_data()
        
        # GPU kullanılabilirse onu seç
        self.device = device
        print(f"Veri hazırlama süresi: {time.time() - start_time:.2f} saniye")
        
    def _extract_user_features(self) -> Tuple[np.ndarray, List[int]]:
        """
        Kullanıcı özelliklerini çıkarır ve normalize eder - geliştirilmiş özellik çıkarma
        """
        print("Kullanıcı özellikleri çıkarılıyor...")
        user_data = []
        user_ids = []
        
        for user in self.users:
            user_id = user['id']
            user_ids.append(user_id)
            
            # Bütçe özellikleri
            min_budget = user['preferredBudget']['min']
            max_budget = user['preferredBudget']['max']
            avg_budget = (min_budget + max_budget) / 2
            budget_range = max_budget - min_budget
            
            # Oda tipi tercihi - one-hot encoding
            is_deluxe = 1 if user['preferredRoomType'] == 'DELUXE' else 0
            is_standard = 1 if user['preferredRoomType'] == 'STANDARD' else 0
            
            # Kapasite
            required_capacity = user['requiredCapacity']
            
            # Tercih edilen özellikler
            has_wifi = 1 if 'WiFi' in user['preferredAmenities'] else 0
            has_tv = 1 if 'TV' in user['preferredAmenities'] else 0
            has_balcony = 1 if 'Balkon' in user['preferredAmenities'] else 0
            has_minibar = 1 if 'Minibar' in user['preferredAmenities'] else 0
            
            # Tercih edilen özellik sayısı
            preferred_amenity_count = len(user['preferredAmenities'])
            
            # Kullanıcı özellik vektörü - daha detaylı
            features = [
                min_budget,        # Minimum bütçe
                max_budget,        # Maksimum bütçe
                avg_budget,        # Ortalama bütçe
                budget_range,      # Bütçe aralığı
                is_deluxe,         # DELUXE oda tercihi
                is_standard,       # STANDARD oda tercihi
                required_capacity, # Gerekli kapasite
                has_wifi,          # WiFi tercihi
                has_tv,            # TV tercihi
                has_balcony,       # Balkon tercihi
                has_minibar,       # Minibar tercihi
                preferred_amenity_count  # Tercih edilen özellik sayısı
            ]
            user_data.append(features)
        
        # Normalize et
        user_features = np.array(user_data, dtype=np.float32)
        scaler = MinMaxScaler()
        user_features = scaler.fit_transform(user_features)
        
        return user_features, user_ids
    
    def _extract_hotel_features(self) -> Tuple[np.ndarray, List[int]]:
        """
        Otel ve oda özelliklerini çıkarır ve normalize eder - geliştirilmiş özellik çıkarma
        """
        print("Otel özellikleri çıkarılıyor...")
        hotel_data = []
        hotel_ids = []
        
        for hotel in self.hotels:
            hotel_id = hotel['id']
            hotel_ids.append(hotel_id)
            
            # Her otel için detaylı özellikler hesapla
            num_rooms = len(hotel['rooms'])
            
            if num_rooms > 0:
                # Fiyat istatistikleri
                room_prices = [room['pricePerNight'] for room in hotel['rooms']]
                avg_price = sum(room_prices) / num_rooms
                min_price = min(room_prices)
                max_price = max(room_prices)
                price_range = max_price - min_price
                
                # Oda tipi istatistikleri
                deluxe_count = sum(1 for room in hotel['rooms'] if room['type'] == 'DELUXE')
                standard_count = sum(1 for room in hotel['rooms'] if room['type'] == 'STANDARD')
                deluxe_ratio = deluxe_count / num_rooms
                standard_ratio = standard_count / num_rooms
                
                # Kapasite istatistikleri
                capacities = [room['capacity'] for room in hotel['rooms']]
                avg_capacity = sum(capacities) / num_rooms
                min_capacity = min(capacities)
                max_capacity = max(capacities)
                
                # Özellik istatistikleri
                wifi_count = sum(1 for room in hotel['rooms'] if room.get('hasWifi', False))
                tv_count = sum(1 for room in hotel['rooms'] if room.get('hasTV', False))
                balcony_count = sum(1 for room in hotel['rooms'] if room.get('hasBalcony', False))
                minibar_count = sum(1 for room in hotel['rooms'] if room.get('hasMinibar', False))
                
                wifi_ratio = wifi_count / num_rooms
                tv_ratio = tv_count / num_rooms
                balcony_ratio = balcony_count / num_rooms
                minibar_ratio = minibar_count / num_rooms
                
                # Toplam özellik oranı
                avg_amenity_count = (wifi_ratio + tv_ratio + balcony_ratio + minibar_ratio)
            else:
                # Default değerler
                avg_price = min_price = max_price = price_range = 0
                deluxe_ratio = standard_ratio = 0
                avg_capacity = min_capacity = max_capacity = 0
                wifi_ratio = tv_ratio = balcony_ratio = minibar_ratio = avg_amenity_count = 0
            
            # Otel özellik vektörü - daha detaylı
            features = [
                avg_price,        # Ortalama oda fiyatı
                min_price,        # Minimum oda fiyatı
                max_price,        # Maksimum oda fiyatı
                price_range,      # Fiyat aralığı
                deluxe_ratio,     # Deluxe oda oranı
                standard_ratio,   # Standard oda oranı
                avg_capacity,     # Ortalama kapasite
                min_capacity,     # Minimum kapasite
                max_capacity,     # Maksimum kapasite
                wifi_ratio,       # WiFi oranı
                tv_ratio,         # TV oranı
                balcony_ratio,    # Balkon oranı
                minibar_ratio,    # Minibar oranı
                avg_amenity_count # Ortalama özellik sayısı
            ]
            hotel_data.append(features)
        
        # Normalize et
        hotel_features = np.array(hotel_data, dtype=np.float32)
        scaler = MinMaxScaler()
        hotel_features = scaler.fit_transform(hotel_features)
        
        return hotel_features, hotel_ids
    
    def _synthesize_interactions(self) -> pd.DataFrame:
        """
        Model eğitimi için geliştirilmiş sentetik kullanıcı-otel etkileşimleri oluşturur
        """
        print("Sentetik etkileşimler oluşturuluyor...")
        interactions = []
        
        # Her kullanıcı için
        for user in tqdm(self.users, desc="Kullanıcı İşleniyor"):
            user_id = user['id']
            user_idx = self.user_id_to_index[user_id]
            
            # Kullanıcı tercihleri
            user_budget_min = user['preferredBudget']['min']
            user_budget_max = user['preferredBudget']['max']
            user_room_type = user['preferredRoomType']
            user_required_capacity = user['requiredCapacity']
            user_amenities = user['preferredAmenities']
            
            # Her otel için kontrol et
            for hotel in self.hotels:
                hotel_id = hotel['id']
                
                if not hotel.get('rooms'):
                    continue
                
                # Uygun odaları bul (kullanıcı bütçesine ve kapasitesine göre)
                suitable_rooms = []
                for room in hotel['rooms']:
                    price_match = user_budget_min <= room['pricePerNight'] <= user_budget_max
                    capacity_match = room['capacity'] >= user_required_capacity
                    
                    if price_match and capacity_match:
                        suitable_rooms.append(room)
                
                # Eğer uygun oda yoksa, bu otel için düşük puan ver
                if not suitable_rooms:
                    rating = random.uniform(1.0, 2.0)  # Düşük puan
                    interactions.append({
                        'user_id': user_id,
                        'hotel_id': hotel_id,
                        'rating': rating
                    })
                    continue
                
                # En uygun odayı seç (tercihen kullanıcının istediği oda tipinde)
                preferred_rooms = [room for room in suitable_rooms if room['type'] == user_room_type]
                selected_room = preferred_rooms[0] if preferred_rooms else suitable_rooms[0]
                
                # Oda özellikleri kontrolü
                amenity_match_count = 0
                if 'WiFi' in user_amenities and selected_room.get('hasWifi', False):
                    amenity_match_count += 1
                if 'TV' in user_amenities and selected_room.get('hasTV', False):
                    amenity_match_count += 1
                if 'Balkon' in user_amenities and selected_room.get('hasBalcony', False):
                    amenity_match_count += 1
                if 'Minibar' in user_amenities and selected_room.get('hasMinibar', False):
                    amenity_match_count += 1
                
                # Özellik uyumu skoru (0-1 arası)
                amenity_score = amenity_match_count / max(1, len(user_amenities))
                
                # Oda tipi uyum skoru
                room_type_score = 1.0 if selected_room['type'] == user_room_type else 0.3
                
                # Fiyat uyum skoru - tercihen orta bütçeye yakın olsun
                user_budget_avg = (user_budget_min + user_budget_max) / 2
                budget_distance = abs(selected_room['pricePerNight'] - user_budget_avg) / user_budget_avg
                price_score = max(0, 1 - budget_distance)
                
                # Toplam puanlamayı hesapla (1-5 arası)
                # Ağırlıklandırılmış skor
                base_rating = 1.0 + 4.0 * (0.4 * price_score + 0.3 * room_type_score + 0.3 * amenity_score)
                
                # Rasgeleleştirme ekle (gerçek verilere benzemesi için)
                noise = np.random.normal(0, 0.2)  # Az gürültü ekle
                rating = min(5, max(1, base_rating + noise))
                
                interactions.append({
                    'user_id': user_id,
                    'hotel_id': hotel_id,
                    'room_id': selected_room['id'],  # Oda ID'sini de ekleyelim
                    'rating': rating
                })
        
        return pd.DataFrame(interactions)
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Modeli eğitmek için eğitim ve test veri kümelerini hazırlar
        """
        print("Eğitim verileri hazırlanıyor...")
        # Etkileşim verisinden özellik matrisi oluştur
        X = []
        y = []
        
        for _, row in self.interactions.iterrows():
            user_id = row['user_id']
            hotel_id = row['hotel_id']
            rating = row['rating']
            
            user_idx = self.user_id_to_index[user_id]
            hotel_idx = self.hotel_id_to_index[hotel_id]
            
            # Kullanıcı ID'si ve otel ID'si
            X.append([user_idx, hotel_idx])
            y.append(rating)
        
        X = np.array(X)
        y = np.array(y, dtype=np.float32)
        
        print(f"Toplam etkileşim sayısı: {len(X)}")
        
        # Eğitim ve test kümelerine ayır - Stratify kullanarak dengeli bir dağılım sağla
        # Puanları kategorik hale getir ve stratify parametresi olarak kullan
        y_binned = np.floor(y).astype(int)  # 1-5 arası tam sayılar
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y_binned
        )
        
        print(f"Eğitim seti boyutu: {len(X_train)}, Test seti boyutu: {len(X_test)}")
        
        return X_train, X_test, y_train, y_test
    
    def __len__(self):
        """DataLoader için veri kümesi boyutu"""
        return len(self.X_train)
    
    def __getitem__(self, idx):
        """DataLoader için öğe alma"""
        user_idx = self.X_train[idx][0]
        hotel_idx = self.X_train[idx][1]
        rating = self.y_train[idx]
        
        # Modelin beklediği formatta veriyi döndür
        return {
            'user_idx': torch.tensor(user_idx, dtype=torch.long),
            'hotel_idx': torch.tensor(hotel_idx, dtype=torch.long),
            'user_features': torch.tensor(self.user_features[user_idx], dtype=torch.float),
            'hotel_features': torch.tensor(self.hotel_features[hotel_idx], dtype=torch.float),
            'rating': torch.tensor(rating, dtype=torch.float)
        }
    
    def get_test_data(self):
        """Test verilerini döndürür"""
        test_data = []
        
        for i in range(len(self.X_test)):
            user_idx = self.X_test[i][0]
            hotel_idx = self.X_test[i][1]
            rating = self.y_test[i]
            
            test_data.append({
                'user_idx': torch.tensor(user_idx, dtype=torch.long),
                'hotel_idx': torch.tensor(hotel_idx, dtype=torch.long),
                'user_features': torch.tensor(self.user_features[user_idx], dtype=torch.float),
                'hotel_features': torch.tensor(self.hotel_features[hotel_idx], dtype=torch.float),
                'rating': torch.tensor(rating, dtype=torch.float)
            })
        
        return test_data 

class ImprovedRecommenderNet(nn.Module):
    """
    İyileştirilmiş Derin Öğrenme Tabanlı Öneri Sistemi için PyTorch Sinir Ağı Modeli
    
    Mimari:
    1. Kullanıcı ve otel ID'leri için geliştirilmiş embedding katmanları
    2. Kullanıcı ve otel özellikleri için çok katmanlı dönüşüm
    3. Embedding ve özellik vektörlerinin gelişmiş birleştirilmesi
    4. Derin sinir ağı katmanları ve dropout düzenleştirmesi
    5. Son katman: Tek değerli çıktı (1-5 arası puanlama)
    """
    
    def __init__(self, num_users: int, num_hotels: int, user_features_dim: int, hotel_features_dim: int):
        """
        Sinir ağı modelini başlatır
        
        Args:
            num_users: Toplam kullanıcı sayısı
            num_hotels: Toplam otel sayısı
            user_features_dim: Kullanıcı özellik vektörünün boyutu
            hotel_features_dim: Otel özellik vektörünün boyutu
        """
        super(ImprovedRecommenderNet, self).__init__()
        
        # Embedding katmanları
        self.user_embedding = nn.Embedding(num_users, EMBEDDING_DIM)
        self.hotel_embedding = nn.Embedding(num_hotels, EMBEDDING_DIM)
        
        # Kullanıcı özellik dönüşümü
        self.user_features_network = nn.Sequential(
            nn.Linear(user_features_dim, EMBEDDING_DIM * 2),
            nn.ReLU(),
            nn.BatchNorm1d(EMBEDDING_DIM * 2),
            nn.Dropout(0.2),
            nn.Linear(EMBEDDING_DIM * 2, EMBEDDING_DIM)
        )
        
        # Otel özellik dönüşümü
        self.hotel_features_network = nn.Sequential(
            nn.Linear(hotel_features_dim, EMBEDDING_DIM * 2),
            nn.ReLU(),
            nn.BatchNorm1d(EMBEDDING_DIM * 2),
            nn.Dropout(0.2),
            nn.Linear(EMBEDDING_DIM * 2, EMBEDDING_DIM)
        )
        
        # Kullanıcı ve otel vektörlerinin birleştirilmesi için dikkat mekanizması
        self.attention = nn.Sequential(
            nn.Linear(EMBEDDING_DIM * 2, EMBEDDING_DIM),
            nn.Tanh(),
            nn.Linear(EMBEDDING_DIM, 1)
        )
        
        # Birleştirilmiş vektör boyutu
        combined_dim = EMBEDDING_DIM * 4  # 2 embedding + 2 özellik dönüşümü
        
        # Derin sinir ağı katmanları
        layers = []
        prev_dim = combined_dim
        
        for i, hidden_dim in enumerate(HIDDEN_LAYERS):
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.BatchNorm1d(hidden_dim))
            # Son katmanda daha az dropout kullan
            dropout_rate = 0.3 if i < len(HIDDEN_LAYERS) - 1 else 0.2
            layers.append(nn.Dropout(dropout_rate))
            prev_dim = hidden_dim
        
        self.hidden_layers = nn.Sequential(*layers)
        
        # Son çıktı katmanı
        self.output_layer = nn.Linear(prev_dim, 1)
        
        # Çıktıyı 1-5 aralığına sınırlamak için sigmoid aktivasyonu ve ölçekleme
        self.rating_activation = lambda x: 1 + 4 * torch.sigmoid(x)
        
        # Ağırlık başlatma
        self._init_weights()
    
    def _init_weights(self):
        """Model ağırlıklarını başlat"""
        # Embedding katmanları için normal dağılım
        nn.init.normal_(self.user_embedding.weight, mean=0, std=0.01)
        nn.init.normal_(self.hotel_embedding.weight, mean=0, std=0.01)
        
        # Linear katmanlar için Xavier başlatma
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def _attention_net(self, user_vec, hotel_vec):
        """Dikkat mekanizması - kullanıcı ve otel arasındaki etkileşimi modellemek için"""
        combined = torch.cat([user_vec, hotel_vec], dim=1)
        attention_weights = torch.softmax(self.attention(combined), dim=1)
        return attention_weights
    
    def forward(self, user_idx, hotel_idx, user_features, hotel_features):
        """
        İleri geçiş (forward pass) fonksiyonu
        """
        # Embedding vektörlerini çıkar
        user_emb = self.user_embedding(user_idx)
        hotel_emb = self.hotel_embedding(hotel_idx)
        
        # Özellikleri dönüştür
        user_feat = self.user_features_network(user_features)
        hotel_feat = self.hotel_features_network(hotel_features)
        
        # Vektörleri birleştir
        combined = torch.cat([user_emb, hotel_emb, user_feat, hotel_feat], dim=1)
        
        # Gizli katmanlardan geçir
        x = self.hidden_layers(combined)
        
        # Son katmandan geçirip puanlamayı oluştur
        rating = self.output_layer(x)
        rating = self.rating_activation(rating)
        
        return rating.squeeze()

class ImprovedLearningRecommender:
    """
    Otel önerilerinde kullanılmak üzere geliştirilmiş derin öğrenme tabanlı öneri sistemi
    """
    
    def __init__(self, users_file: str, hotels_file: str, model_path: str = "improved_hotel_recommender_model.pth"):
        """
        Geliştirilmiş derin öğrenme tabanlı öneri sistemini başlatır
        
        Args:
            users_file: Kullanıcı verileri JSON dosyasının yolu
            hotels_file: Otel verileri JSON dosyasının yolu
            model_path: Eğitilmiş modelin kaydedileceği/yükleneceği dosya yolu
        """
        start_time = time.time()
        print("İyileştirilmiş öneri sistemi başlatılıyor...")
        
        # Veri kümesini başlat
        self.dataset = ImprovedHotelDataset(users_file, hotels_file)
        
        # Model dosya yolu
        self.model_path = model_path
        
        # Model oluştur
        self.model = ImprovedRecommenderNet(
            num_users=self.dataset.num_users,
            num_hotels=self.dataset.num_hotels,
            user_features_dim=self.dataset.num_user_features,
            hotel_features_dim=self.dataset.num_hotel_features
        ).to(self.dataset.device)
        
        # Eğer daha önce kaydedilmiş bir model varsa yükle
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=self.dataset.device))
            self.model.eval()
            print(f"Kaydedilmiş model '{model_path}' başarıyla yüklendi.")
        else:
            print("Kaydedilmiş model bulunamadı. Eğitim gerekiyor.")
            
        print(f"Öneri sistemi başlatma süresi: {time.time() - start_time:.2f} saniye")
    
    def train(self, evaluate: bool = True):
        """
        Öneri modelini geliştirilmiş stratejilerle eğitir
        
        Args:
            evaluate: Eğitim sonrası değerlendirme yapılıp yapılmayacağı
        """
        # DataLoader oluştur
        train_loader = DataLoader(
            self.dataset, 
            batch_size=BATCH_SIZE, 
            shuffle=True,
            num_workers=0,  # Windows'ta sorun çıkabiliyor, ihtiyaca göre artırılabilir
            pin_memory=True if torch.cuda.is_available() else False
        )
        
        # Optimizasyon ve kayıp fonksiyonunu tanımla
        optimizer = optim.Adam(self.model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)
        
        # Öğrenme oranı zamanlayıcısı ekle
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5, verbose=True, min_lr=1e-6
        )
        
        # MSE kaybını kullan
        criterion = nn.MSELoss()
        
        # Eğitim döngüsü
        self.model.train()
        loss_history = []
        val_loss_history = []
        
        # Eğitim ve doğrulama verisini ayır
        train_size = int(0.9 * len(self.dataset.X_train))
        indices = list(range(len(self.dataset.X_train)))
        np.random.shuffle(indices)
        train_indices, val_indices = indices[:train_size], indices[train_size:]
        
        print(f"Model eğitimi başlatılıyor... Toplam {NUM_EPOCHS} epoch")
        print(f"GPU kullanımı: {self.dataset.device}")
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(NUM_EPOCHS):
            epoch_start_time = time.time()
            
            # Eğitim aşaması
            self.model.train()
            epoch_loss = 0
            batch_count = 0
            
            with tqdm(train_loader, desc=f"Epoch {epoch+1}/{NUM_EPOCHS}") as pbar:
                for batch in pbar:
                    # Batch'i cihaza taşı
                    user_idx = batch['user_idx'].to(self.dataset.device)
                    hotel_idx = batch['hotel_idx'].to(self.dataset.device)
                    user_features = batch['user_features'].to(self.dataset.device)
                    hotel_features = batch['hotel_features'].to(self.dataset.device)
                    ratings = batch['rating'].to(self.dataset.device)
                    
                    # Gradyanları sıfırla
                    optimizer.zero_grad()
                    
                    # İleri geçiş
                    predictions = self.model(user_idx, hotel_idx, user_features, hotel_features)
                    
                    # Kaybı hesapla
                    loss = criterion(predictions, ratings)
                    
                    # Geri yayılım
                    loss.backward()
                    
                    # Gradyan kesme (exploding gradient sorununu önlemek için)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    
                    # Parametreleri güncelle
                    optimizer.step()
                    
                    # Kaybı topla
                    epoch_loss += loss.item()
                    batch_count += 1
                    
                    # Progress bar güncelle
                    pbar.set_postfix({"loss": f"{loss.item():.4f}"})
            
            # Epoch sonunda kaybı göster
            avg_loss = epoch_loss / max(1, batch_count)
            loss_history.append(avg_loss)
            
            # Doğrulama aşaması
            self.model.eval()
            val_loss = 0
            val_samples = 0
            
            with torch.no_grad():
                for idx in val_indices:
                    sample = self.dataset[idx]
                    user_idx = sample['user_idx'].unsqueeze(0).to(self.dataset.device)
                    hotel_idx = sample['hotel_idx'].unsqueeze(0).to(self.dataset.device)
                    user_features = sample['user_features'].unsqueeze(0).to(self.dataset.device)
                    hotel_features = sample['hotel_features'].unsqueeze(0).to(self.dataset.device)
                    rating = sample['rating'].unsqueeze(0).to(self.dataset.device)
                    
                    prediction = self.model(user_idx, hotel_idx, user_features, hotel_features)
                    val_loss += criterion(prediction, rating).item()
                    val_samples += 1
            
            avg_val_loss = val_loss / max(1, val_samples)
            val_loss_history.append(avg_val_loss)
            
            # Öğrenme oranı zamanlayıcısını güncelle
            scheduler.step(avg_val_loss)
            
            # Epoch süresini hesapla
            epoch_time = time.time() - epoch_start_time
            
            # Early stopping kontrolü
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                patience_counter = 0
                # En iyi model olarak kaydet
                torch.save(self.model.state_dict(), self.model_path)
                print(f"Epoch {epoch+1}/{NUM_EPOCHS}, Eğitim Kaybı: {avg_loss:.4f}, Doğrulama Kaybı: {avg_val_loss:.4f}, Süre: {epoch_time:.1f}s - Model kaydedildi!")
            else:
                patience_counter += 1
                print(f"Epoch {epoch+1}/{NUM_EPOCHS}, Eğitim Kaybı: {avg_loss:.4f}, Doğrulama Kaybı: {avg_val_loss:.4f}, Süre: {epoch_time:.1f}s")
                
                # Sabırsızlık kontrolü (early stopping)
                if patience_counter >= EARLY_STOPPING_PATIENCE:
                    print(f"Early stopping! {EARLY_STOPPING_PATIENCE} epoch boyunca iyileşme olmadı.")
                    break
        
        # En iyi modeli yükle
        self.model.load_state_dict(torch.load(self.model_path))
        print(f"En iyi model '{self.model_path}' başarıyla yüklendi.")
        
        # Eğitim sonrası değerlendirme
        if evaluate:
            self.evaluate()
            
        # Eğitim kaybı grafiğini çiz
        plt.figure(figsize=(10, 6))
        plt.plot(loss_history, label='Eğitim Kaybı')
        plt.plot(val_loss_history, label='Doğrulama Kaybı')
        plt.title('Eğitim ve Doğrulama Kaybı Değişimi')
        plt.xlabel('Epoch')
        plt.ylabel('MSE Kaybı')
        plt.legend()
        plt.grid(True)
        plt.savefig('improved_training_loss.png')
        print("Eğitim kaybı grafiği 'improved_training_loss.png' olarak kaydedildi.")
        
    def evaluate(self):
        """
        Modeli test verileri üzerinde değerlendirir ve detaylı metrikler üretir
        """
        print("\nModel değerlendiriliyor...")
        self.model.eval()
        test_data = self.dataset.get_test_data()
        criterion = nn.MSELoss()
        
        total_loss = 0
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            for sample in tqdm(test_data, desc="Test örnekleri işleniyor"):
                user_idx = sample['user_idx'].to(self.dataset.device)
                hotel_idx = sample['hotel_idx'].to(self.dataset.device)
                user_features = sample['user_features'].to(self.dataset.device)
                hotel_features = sample['hotel_features'].to(self.dataset.device)
                rating = sample['rating'].to(self.dataset.device)
                
                # Tahmin yap
                prediction = self.model(
                    user_idx.unsqueeze(0), 
                    hotel_idx.unsqueeze(0), 
                    user_features.unsqueeze(0), 
                    hotel_features.unsqueeze(0)
                )
                
                # Kaybı hesapla
                loss = criterion(prediction, rating)
                total_loss += loss.item()
                
                all_predictions.append(prediction.item())
                all_targets.append(rating.item())
        
        # Ortalama karesel hata
        mse = total_loss / len(test_data)
        rmse = np.sqrt(mse)
        
        # Ortalama mutlak hata
        mae = np.mean(np.abs(np.array(all_predictions) - np.array(all_targets)))
        
        # 0.5 puanlık tolerans içindeki tahminlerin oranı
        tolerance = 0.5
        within_tolerance = np.mean(np.abs(np.array(all_predictions) - np.array(all_targets)) <= tolerance)
        
        print(f"Test MSE: {mse:.4f}")
        print(f"Test RMSE: {rmse:.4f}")
        print(f"Test MAE: {mae:.4f}")
        print(f"{tolerance} puan tolerans içindeki tahminler: {within_tolerance*100:.2f}%")
        
        # Tahminler vs gerçek değerler grafiği
        plt.figure(figsize=(10, 6))
        plt.scatter(all_targets, all_predictions, alpha=0.5)
        plt.plot([1, 5], [1, 5], 'r--')  # Mükemmel tahmin çizgisi
        
        # Tolerans aralığı
        x = np.linspace(1, 5, 100)
        plt.fill_between(x, x - tolerance, x + tolerance, alpha=0.2, color='green')
        
        plt.xlim(1, 5)
        plt.ylim(1, 5)
        plt.xlabel('Gerçek Puanlar')
        plt.ylabel('Tahmin Edilen Puanlar')
        plt.title('Tahmin vs Gerçek Değerler')
        plt.grid(True)
        plt.savefig('improved_predictions_vs_targets.png')
        print("Tahmin değerlendirme grafiği 'improved_predictions_vs_targets.png' olarak kaydedildi.")
        
    def recommend_hotels(self, user_id: int, top_n: int = 5, debug: bool = False) -> List[Dict[str, Any]]:
        """
        Bir kullanıcı için en uygun otelleri önerir
        Bütçe, oda tipi tercihi ve kapasite gibi kısıtları dikkate alır
        
        Args:
            user_id: Kullanıcı ID'si
            top_n: Önerilecek otel sayısı
            debug: Ayrıntılı bilgi gösterme modu
            
        Returns:
            Önerilen otellerin listesi
        """
        print(f"\n{user_id} ID'li kullanıcı için otel önerileri hazırlanıyor...")
        start_time = time.time()
        self.model.eval()
        
        # Kullanıcı verileri
        with open(self.dataset.users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        # Otel verileri
        with open(self.dataset.hotels_file, 'r', encoding='utf-8') as f:
            hotels = json.load(f)
        
        try:
            user_idx = self.dataset.user_id_to_index.get(user_id)
            if user_idx is None:
                print(f"Uyarı: {user_id} ID'li kullanıcı bulunamadı.")
                return []
                
            user = next(u for u in users if u['id'] == user_id)
            user_features = torch.tensor(self.dataset.user_features[user_idx], dtype=torch.float).to(self.dataset.device)
            
            print(f"Kullanıcı Bilgileri:")
            print(f"- İsim: {user['name']}")
            print(f"- Bütçe: {user['preferredBudget']['min']}-{user['preferredBudget']['max']} TL")
            print(f"- Tercih edilen oda tipi: {user['preferredRoomType']}")
            print(f"- Gerekli kapasite: {user['requiredCapacity']}")
            print(f"- Tercih edilen özellikler: {', '.join(user['preferredAmenities'])}")
            
            # Tüm otel-oda kombinasyonları için tahminler yap
            all_predictions = []
            
            for hotel in tqdm(hotels, desc="Oteller değerlendiriliyor"):
                hotel_id = hotel['id']
                hotel_idx = self.dataset.hotel_id_to_index.get(hotel_id)
                
                if hotel_idx is None or not hotel.get('rooms'):
                    continue
                    
                hotel_features = torch.tensor(self.dataset.hotel_features[hotel_idx], dtype=torch.float).to(self.dataset.device)
                
                # Modelin tahminini al - genel otel puanı
                with torch.no_grad():
                    base_prediction = self.model(
                        torch.tensor(user_idx, dtype=torch.long).unsqueeze(0).to(self.dataset.device),
                        torch.tensor(hotel_idx, dtype=torch.long).unsqueeze(0).to(self.dataset.device),
                        user_features.unsqueeze(0),
                        hotel_features.unsqueeze(0)
                    ).item()
                
                # Oteldeki her oda için uygunluğu değerlendir
                for room in hotel['rooms']:
                    # Kapasite kontrolü - Kritik bir kısıt olarak kullan
                    if room['capacity'] < user['requiredCapacity']:
                        if debug:
                            print(f"Oda {room['id']} kapasitesi yetersiz. Gerekli: {user['requiredCapacity']}, Mevcut: {room['capacity']}")
                        continue
                    
                    room_score = base_prediction
                    adjustment_factors = []
                    
                    # Bütçe uyumu kontrolü
                    min_budget = user['preferredBudget']['min']
                    max_budget = user['preferredBudget']['max']
                    room_price = room['pricePerNight']
                    budget_factor = 1.0
                    
                    # Bütçe dışındaysa puanını düşür
                    if room_price < min_budget * 0.8:
                        budget_factor = 0.9  # Çok ucuz
                        adjustment_factors.append(f"Bütçe altı ({room_price} < {min_budget}): x0.9")
                    elif room_price > max_budget * 1.2:
                        budget_factor = 0.5  # Çok pahalı
                        adjustment_factors.append(f"Bütçe üstü ({room_price} > {max_budget}): x0.5")
                    elif room_price < min_budget:
                        budget_factor = 0.95  # Biraz ucuz
                        adjustment_factors.append(f"Biraz bütçe altı: x0.95")
                    elif room_price > max_budget:
                        budget_factor = 0.7  # Biraz pahalı
                        adjustment_factors.append(f"Biraz bütçe üstü: x0.7")
                    else:
                        budget_factor = 1.1  # Bütçeye tam uygun, bonus puan
                        adjustment_factors.append(f"Bütçeye uygun: x1.1")
                    
                    room_score *= budget_factor
                    
                    # Oda tipi kontrolü
                    type_factor = 1.0
                    if room['type'] == user['preferredRoomType']:
                        type_factor = 1.2  # Tercih edilen oda tipi, bonus puan
                        adjustment_factors.append(f"Tercih edilen oda tipi: x1.2")
                    else:
                        type_factor = 0.8  # Farklı oda tipi
                        adjustment_factors.append(f"Farklı oda tipi: x0.8")
                    
                    room_score *= type_factor
                    
                    # Özellik eşleşmesi
                    amenity_match_count = 0
                    amenity_count = len(user['preferredAmenities'])
                    
                    if amenity_count > 0:
                        if 'WiFi' in user['preferredAmenities'] and room.get('hasWifi', False):
                            amenity_match_count += 1
                        if 'TV' in user['preferredAmenities'] and room.get('hasTV', False):
                            amenity_match_count += 1
                        if 'Balkon' in user['preferredAmenities'] and room.get('hasBalcony', False):
                            amenity_match_count += 1
                        if 'Minibar' in user['preferredAmenities'] and room.get('hasMinibar', False):
                            amenity_match_count += 1
                        
                        amenity_match_ratio = amenity_match_count / amenity_count
                        
                        # Özellik eşleşmesi puanı etkileyecek
                        amenity_factor = 0.8 + 0.4 * amenity_match_ratio
                        adjustment_factors.append(f"Özellik eşleşmesi ({amenity_match_count}/{amenity_count}): x{amenity_factor:.2f}")
                        room_score *= amenity_factor
                    
                    # Son puan için maks ve min değerler arasında sınırla
                    room_score = min(5.0, max(1.0, room_score))
                    
                    # Oda durumu kontrolü
                    if room.get('status') != 'AVAILABLE':
                        continue  # Müsait olmayan odaları öneri listesine alma
                    
                    recommendation_info = {
                        'hotel_id': hotel_id,
                        'hotel_name': hotel['name'],
                        'room_id': room['id'],
                        'room_name': room['name'],
                        'room_type': room['type'],
                        'price': room['pricePerNight'],
                        'city': hotel['city'],
                        'address': hotel['address'],
                        'capacity': room['capacity'],
                        'predicted_rating': round(room_score, 2),
                        'base_score': round(base_prediction, 2),
                        'score_details': adjustment_factors if debug else None,
                        'amenities': {
                            'wifi': room.get('hasWifi', False),
                            'tv': room.get('hasTV', False),
                            'balcony': room.get('hasBalcony', False),
                            'minibar': room.get('hasMinibar', False)
                        }
                    }
                    
                    all_predictions.append(recommendation_info)
            
            # En yüksek puanlı oda önerilerini seç
            top_recommendations = sorted(all_predictions, key=lambda x: x['predicted_rating'], reverse=True)[:top_n]
            
            # Daha açıklayıcı öneri türü ekle
            for rec in top_recommendations:
                match_reasons = []
                if rec['price'] <= user['preferredBudget']['max'] and rec['price'] >= user['preferredBudget']['min']:
                    match_reasons.append("bütçeye uygun")
                
                if rec['room_type'] == user['preferredRoomType']:
                    match_reasons.append("tercih edilen oda tipi")
                
                amenities_user_wanted = []
                for amenity in user['preferredAmenities']:
                    if amenity == 'WiFi' and rec['amenities']['wifi']:
                        amenities_user_wanted.append("WiFi")
                    elif amenity == 'TV' and rec['amenities']['tv']:
                        amenities_user_wanted.append("TV")
                    elif amenity == 'Balkon' and rec['amenities']['balcony']:
                        amenities_user_wanted.append("Balkon")
                    elif amenity == 'Minibar' and rec['amenities']['minibar']:
                        amenities_user_wanted.append("Minibar")
                
                if amenities_user_wanted:
                    match_reasons.append(f"istenen özellikler: {', '.join(amenities_user_wanted)}")
                
                if match_reasons:
                    rec['recommendation_type'] = f"Bu oda şu açılardan size uygun: {', '.join(match_reasons)}"
                else:
                    rec['recommendation_type'] = "Alternatif Öneri"
            
            print(f"Öneri süresi: {time.time() - start_time:.2f} saniye")
            return top_recommendations
            
        except Exception as e:
            print(f"Öneri oluşturulurken hata: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def explain_recommendation(self, user_id: int, hotel_id: int) -> Dict[str, Any]:
        """
        Belirli bir otel önerisini ayrıntılı şekilde açıklar
        
        Args:
            user_id: Kullanıcı ID'si
            hotel_id: Otel ID'si
            
        Returns:
            Öneri açıklaması
        """
        try:
            self.model.eval()
            
            # Kullanıcı ve otel verileri
            with open(self.dataset.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            with open(self.dataset.hotels_file, 'r', encoding='utf-8') as f:
                hotels = json.load(f)
            
            # Kullanıcı ve otel indekslerini ve özelliklerini al
            user_idx = self.dataset.user_id_to_index.get(user_id)
            hotel_idx = self.dataset.hotel_id_to_index.get(hotel_id)
            
            if user_idx is None or hotel_idx is None:
                return {"error": "Kullanıcı veya otel bulunamadı"}
            
            user = next((u for u in users if u['id'] == user_id), None)
            hotel = next((h for h in hotels if h['id'] == hotel_id), None)
            
            if not user or not hotel:
                return {"error": "Kullanıcı veya otel verileri bulunamadı"}
            
            user_features = self.dataset.user_features[user_idx]
            hotel_features = self.dataset.hotel_features[hotel_idx]
            
            # Model kullanarak tahmini puanı al
            user_tensor = torch.tensor(user_idx, dtype=torch.long).unsqueeze(0).to(self.dataset.device)
            hotel_tensor = torch.tensor(hotel_idx, dtype=torch.long).unsqueeze(0).to(self.dataset.device)
            user_feat_tensor = torch.tensor(user_features, dtype=torch.float).unsqueeze(0).to(self.dataset.device)
            hotel_feat_tensor = torch.tensor(hotel_features, dtype=torch.float).unsqueeze(0).to(self.dataset.device)
            
            with torch.no_grad():
                predicted_score = self.model(user_tensor, hotel_tensor, user_feat_tensor, hotel_feat_tensor).item()
            
            # Kullanıcı ve otel özelliklerinin karşılaştırmalı analizi
            user_budget_min = user['preferredBudget']['min']
            user_budget_max = user['preferredBudget']['max']
            user_preferred_type = user['preferredRoomType']
            user_required_capacity = user['requiredCapacity']
            user_preferred_amenities = user['preferredAmenities']
            
            # En iyi eşleşen odayı bul
            best_matching_room = None
            best_room_score = 0
            
            room_matches = []
            
            for room in hotel['rooms']:
                score = 0
                matches = []
                mismatches = []
                
                # Bütçe uyumu
                if user_budget_min <= room['pricePerNight'] <= user_budget_max:
                    score += 2
                    matches.append(f"Oda fiyatı ({room['pricePerNight']} TL) bütçenize ({user_budget_min}-{user_budget_max} TL) uygun")
                elif room['pricePerNight'] < user_budget_min:
                    score += 1
                    matches.append(f"Oda fiyatı ({room['pricePerNight']} TL) bütçenizin altında")
                else:
                    mismatches.append(f"Oda fiyatı ({room['pricePerNight']} TL) bütçenizin ({user_budget_max} TL) üstünde")
                
                # Oda tipi
                if room['type'] == user_preferred_type:
                    score += 2
                    matches.append(f"Tercih ettiğiniz oda tipi: {user_preferred_type}")
                else:
                    mismatches.append(f"Farklı oda tipi: {room['type']} (tercih: {user_preferred_type})")
                
                # Kapasite
                if room['capacity'] >= user_required_capacity:
                    score += 1
                    matches.append(f"Yeterli kapasite: {room['capacity']} kişilik (ihtiyaç: {user_required_capacity})")
                else:
                    score -= 3  # Kapasite çok önemli bir kriter
                    mismatches.append(f"Yetersiz kapasite: {room['capacity']} kişilik (ihtiyaç: {user_required_capacity})")
                
                # Özellikler
                for amenity in user_preferred_amenities:
                    if amenity == 'WiFi' and room.get('hasWifi', False):
                        score += 0.5
                        matches.append("WiFi mevcut")
                    elif amenity == 'TV' and room.get('hasTV', False):
                        score += 0.5
                        matches.append("TV mevcut")
                    elif amenity == 'Balkon' and room.get('hasBalcony', False):
                        score += 0.5
                        matches.append("Balkon mevcut")
                    elif amenity == 'Minibar' and room.get('hasMinibar', False):
                        score += 0.5
                        matches.append("Minibar mevcut")
                    else:
                        if amenity == 'WiFi':
                            mismatches.append("WiFi mevcut değil")
                        elif amenity == 'TV':
                            mismatches.append("TV mevcut değil")
                        elif amenity == 'Balkon':
                            mismatches.append("Balkon mevcut değil")
                        elif amenity == 'Minibar':
                            mismatches.append("Minibar mevcut değil")
                
                room_matches.append({
                    "room_id": room['id'],
                    "room_name": room['name'],
                    "room_type": room['type'],
                    "capacity": room['capacity'],
                    "price": room['pricePerNight'],
                    "score": score,
                    "matches": matches,
                    "mismatches": mismatches
                })
                
                if score > best_room_score:
                    best_room_score = score
                    best_matching_room = room
            
            # Açıklama metni oluştur
            if best_matching_room:
                best_room = next((r for r in room_matches if r["room_id"] == best_matching_room['id']), None)
                
                explanation_text = f"Bu otel sizin için {predicted_score:.1f}/5.0 puan ile değerlendirildi. "
                
                if best_room["matches"]:
                    explanation_text += f"En iyi eşleşen oda '{best_matching_room['name']}', çünkü: "
                    explanation_text += ", ".join(best_room["matches"]) + ". "
                
                if best_room["mismatches"]:
                    explanation_text += "Dikkat edilmesi gereken noktalar: "
                    explanation_text += ", ".join(best_room["mismatches"]) + "."
            else:
                explanation_text = "Bu otelde size uygun bir oda bulunamadı."
            
            return {
                "hotel_name": hotel['name'],
                "predicted_score": round(predicted_score, 2),
                "explanation": explanation_text,
                "best_matching_room": best_matching_room['name'] if best_matching_room else None,
                "room_matches": sorted(room_matches, key=lambda x: x["score"], reverse=True)
            }
            
        except Exception as e:
            return {"error": str(e)}

# Örnek kullanım
if __name__ == "__main__":
    # Genişletilmiş veri setini kullan
    users_file = 'datas/expanded_users.json'
    hotels_file = 'datas/expanded_hotels.json'
    
    # Eğer genişletilmiş veri seti yoksa, orijinal veri setini kullan
    if not os.path.exists(users_file):
        users_file = 'datas/mock_users.json'
    if not os.path.exists(hotels_file):
        hotels_file = 'datas/mock_nevsehir_hotels.json'
    
    print(f"Kullanılan veri setleri: {users_file}, {hotels_file}")
    
    # İyileştirilmiş öneri sistemini başlat
    recommender = ImprovedLearningRecommender(users_file, hotels_file)
    
    # RTX 3060 Ti ekran kartı için optimize edilmiş eğitim
    recommender.train()
    
    # Test edilecek kullanıcılar
    test_user_ids = [1, 2, 3]  # Örnek kullanıcılar
    
    # Her kullanıcı için öneriler al ve değerlendir
    for user_id in test_user_ids:
        print(f"\n{'='*80}")
        print(f"Kullanıcı ID: {user_id} için öneriler:")
        
        recommendations = recommender.recommend_hotels(user_id, top_n=3, debug=True)
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['hotel_name']} - {rec['room_name']}")
            print(f"   Tahmini Puan: {rec['predicted_rating']}")
            print(f"   Oda Tipi: {rec['room_type']}")
            print(f"   Fiyat: {rec['price']} TL")
            print(f"   Kapasite: {rec['capacity']} kişilik")
            print(f"   Özellikler: " + ", ".join([k for k, v in rec['amenities'].items() if v]))
            print(f"   Öneri Açıklaması: {rec['recommendation_type']}")
            
            if rec.get('score_details'):
                print(f"   Puan Detayları: {', '.join(rec['score_details'])}")
            
            # Her bir öneri için detaylı açıklama göster (sadece ilk için değil)
            explanation = recommender.explain_recommendation(user_id, rec['hotel_id'])
            if "error" not in explanation:
                print(f"\n   Detaylı Açıklama: {explanation['explanation']}")
                
                # En iyi eşleşen odayı göster
                best_room = next((r for r in explanation['room_matches'] if r["room_name"] == rec['room_name']), None)
                if best_room:
                    print(f"   Eşleşen Özellikler:")
                    for match in best_room['matches']:
                        print(f"     ✓ {match}")
                    
                    if best_room['mismatches']:
                        print(f"   Eşleşmeyen Özellikler:")
                        for mismatch in best_room['mismatches']:
                            print(f"     ✗ {mismatch}")
            else:
                print(f"   Açıklama alınamadı: {explanation['error']}") 