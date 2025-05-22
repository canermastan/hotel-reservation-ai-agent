import React, { useState, useRef, useEffect } from 'react';
import { StyleSheet, View, ScrollView, TextInput, TouchableOpacity, SafeAreaView, Platform, Image, KeyboardAvoidingView, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';

import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';

// Session ve kullanıcı ID'leri
const USER_ID = 'u_123';
const APP_NAME = 'multi_tool_agent';
const API_BASE_URL = 'http://172.20.10.14:8000';

// UUID oluşturma fonksiyonu
const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

export default function AIAssistantScreen() {
  const router = useRouter();
  const scrollViewRef = useRef<ScrollView>(null);
  
  const [sessionId, setSessionId] = useState('');
  const [aiMessage, setAiMessage] = useState('');
  const [agentMessages, setAgentMessages] = useState<{text: string, isUser: boolean}[]>([
    {text: 'Merhaba! Ben Kapadokya Hackathon AI Asistanınız. Size nasıl yardımcı olabilirim?', isUser: false}
  ]);
  const [isAgentTyping, setIsAgentTyping] = useState(false);
  
  // Component mount olduğunda yeni session başlat
  useEffect(() => {
    console.log("Component mount - yeni session başlatılıyor...");
    const newSessionId = `s_${generateUUID()}`;
    console.log("Oluşturulan session ID:", newSessionId);
    setSessionId(newSessionId);
    initializeSession(newSessionId);
  }, []);

  // Session başlatma fonksiyonu
  const initializeSession = async (newSessionId: string) => {
    try {
      console.log(`${API_BASE_URL}/apps/${APP_NAME}/users/${USER_ID}/sessions/${newSessionId} adresine istek gönderiliyor...`);
      const response = await fetch(`${API_BASE_URL}/apps/${APP_NAME}/users/${USER_ID}/sessions/${newSessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          state: {
            key1: "value1",
            key2: 42
          }
        })
      });

      console.log("Session başlatma isteği yanıt durumu:", response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error("Session başlatma hatası:", errorText);
        throw new Error(`Session başlatılamadı: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log('Session başarıyla başlatıldı:', data);
      console.log('Aktif session ID:', newSessionId);
    } catch (error) {
      console.error('Session başlatma hatası:', error);
    }
  };

  // Mesaj gönderme fonksiyonu
  const sendMessageToAgent = async () => {
    if (!aiMessage.trim()) return;
    
    if (!sessionId) {
      console.error("Session ID bulunamadı! Yeni bir oturum başlatılıyor...");
      const newSessionId = `s_${generateUUID()}`;
      setSessionId(newSessionId);
      await initializeSession(newSessionId);
      // Oturum başlatma işleminden sonra, bu fonksiyonun tekrar çağrılmasını sağla
      setTimeout(() => sendMessageToAgent(), 1000);
      return;
    }
    
    console.log("Mesaj gönderiliyor, kullanılan session ID:", sessionId);
    
    // Kullanıcı mesajını ekle
    const newMessages = [...agentMessages, {text: aiMessage, isUser: true}];
    setAgentMessages(newMessages);
    setAiMessage('');
    
    // AI yanıt veriyor görüntüsü
    setIsAgentTyping(true);
    
    try {
      console.log('Gönderilen istek:', {
        app_name: APP_NAME,
        user_id: USER_ID,
        session_id: sessionId,
        new_message: {
          role: "user",
          parts: [{
            text: aiMessage
          }]
        }
      });

      const response = await fetch(`${API_BASE_URL}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          app_name: APP_NAME,
          user_id: USER_ID,
          session_id: sessionId,
          new_message: {
            role: "user",
            parts: [{
              text: aiMessage
            }]
          }
        })
      });

      console.log('API yanıt durumu:', response.status);
      const responseText = await response.text();
      console.log('API yanıt metni:', responseText);

      if (!response.ok) {
        const errorData = JSON.parse(responseText);
        throw new Error(errorData.detail || 'Mesaj gönderilemedi');
      }

      const data = JSON.parse(responseText);
      console.log('API yanıtı (parse edilmiş):', data);
      
      // AI yanıtını ekle
      if (Array.isArray(data)) {
        // En son model yanıtını bul
        const lastModelResponse = data
          .filter(item => item.content?.role === 'model')
          .pop();

        if (lastModelResponse?.content?.parts?.[0]?.text) {
          setAgentMessages([...newMessages, {text: lastModelResponse.content.parts[0].text, isUser: false}]);
        } else {
          console.log('Model yanıtı bulunamadı:', data);
          setAgentMessages([...newMessages, {text: 'Üzgünüm, bir yanıt alınamadı.', isUser: false}]);
        }
      } else {
        console.log('Yanıt array değil:', data);
        setAgentMessages([...newMessages, {text: 'Üzgünüm, bir yanıt alınamadı.', isUser: false}]);
      }
    } catch (error: any) {
      console.error('Mesaj gönderme hatası:', error);
      console.error('Hata detayı:', error.message);
      setAgentMessages([...newMessages, {text: error?.message || 'Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.', isUser: false}]);
    } finally {
      setIsAgentTyping(false);
    }
  };
  
  // Mesajlar değiştiğinde otomatik olarak en alta kaydır
  useEffect(() => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, [agentMessages, isAgentTyping]);
  
  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <LinearGradient
        colors={['#6a41bd', '#4A6DA7']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0 }}
        style={styles.header}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        
        <View style={styles.headerContent}>
          <View style={styles.avatarContainer}>
            <Ionicons name="sparkles" size={22} color="#fff" />
          </View>
          <View>
            <ThemedText style={styles.headerTitle}>Kapadokya Hackathon AI</ThemedText>
            <ThemedText style={styles.headerSubtitle}>Kişisel Asistanınız</ThemedText>
          </View>
        </View>
      </LinearGradient>
      
      {/* Chat içeriği */}
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardAvoidContainer}>
        <ScrollView
          ref={scrollViewRef}
          style={styles.chatContainer}
          contentContainerStyle={styles.chatContent}
          showsVerticalScrollIndicator={false}>
          
          {/* Mesajlar */}
          {agentMessages.map((msg, index) => (
            <View 
              key={index} 
              style={[
                styles.messageContainer,
                msg.isUser ? styles.userMessageContainer : styles.botMessageContainer
              ]}>
              {!msg.isUser && (
                <View style={styles.botAvatar}>
                  <Ionicons name="sparkles" size={16} color="#fff" />
                </View>
              )}
              <View
                style={[
                  styles.messageBubble,
                  msg.isUser ? styles.userMessageBubble : styles.botMessageBubble
                ]}>
                <ThemedText 
                  style={[
                    styles.messageText,
                    msg.isUser && styles.userMessageText
                  ]}>
                  {msg.text}
                </ThemedText>
              </View>
            </View>
          ))}
          
          {/* Typing indicator */}
          {isAgentTyping && (
            <View style={styles.botMessageContainer}>
              <View style={styles.botAvatar}>
                <Ionicons name="sparkles" size={16} color="#fff" />
              </View>
              <View style={[styles.messageBubble, styles.botMessageBubble, styles.typingBubble]}>
                <View style={styles.typingIndicator}>
                  <View style={styles.typingDot} />
                  <View style={[styles.typingDot, styles.typingDotMiddle]} />
                  <View style={styles.typingDot} />
                </View>
              </View>
            </View>
          )}
        </ScrollView>
        
        {/* Input alanı */}
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.textInput}
            placeholder="Kapadokya hakkında bir şey sorun..."
            placeholderTextColor="#999"
            value={aiMessage}
            onChangeText={setAiMessage}
            multiline
          />
          <TouchableOpacity
            style={styles.sendButton}
            onPress={sendMessageToAgent}
            disabled={!aiMessage.trim()}>
            <LinearGradient
              colors={aiMessage.trim() ? ['#6a41bd', '#4A6DA7'] : ['#ccc', '#999']}
              style={styles.sendButtonGradient}>
              <Ionicons 
                name="send" 
                size={20} 
                color="#fff" 
              />
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
  header: {
    height: Platform.OS === 'ios' ? 100 : 80,
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: Platform.OS === 'ios' ? 30 : 10,
    paddingHorizontal: 15,
  },
  backButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 20,
    marginRight: 15,
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatarContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  headerSubtitle: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.8)',
  },
  keyboardAvoidContainer: {
    flex: 1,
  },
  chatContainer: {
    flex: 1,
  },
  chatContent: {
    padding: 15,
    paddingBottom: 30,
  },
  infoCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    overflow: 'hidden',
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 5,
    elevation: 2,
  },
  infoCardImage: {
    width: '100%',
    height: 120,
    resizeMode: 'cover',
  },
  infoCardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    paddingHorizontal: 15,
    paddingTop: 15,
    paddingBottom: 5,
  },
  infoCardSubtitle: {
    fontSize: 14,
    paddingHorizontal: 15,
    paddingBottom: 15,
    color: '#666',
  },
  messageContainer: {
    flexDirection: 'row',
    marginBottom: 15,
    alignItems: 'flex-end',
  },
  userMessageContainer: {
    justifyContent: 'flex-end',
  },
  botMessageContainer: {
    justifyContent: 'flex-start',
  },
  botAvatar: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#6a41bd',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  messageBubble: {
    maxWidth: '75%',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 18,
  },
  userMessageBubble: {
    backgroundColor: '#6a41bd',
    borderTopRightRadius: 4,
  },
  botMessageBubble: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 20,
  },
  userMessageText: {
    color: '#fff',
  },
  typingBubble: {
    paddingVertical: 15,
    paddingHorizontal: 15,
  },
  typingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  typingDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: '#6a41bd',
    marginHorizontal: 2,
    opacity: 0.5,
  },
  typingDotMiddle: {
    opacity: 0.7,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 15,
    paddingTop: 10,
    paddingBottom: Platform.OS === 'ios' ? 30 : 15,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  textInput: {
    flex: 1,
    backgroundColor: '#f1f3f8',
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingTop: 10,
    paddingBottom: 10,
    minHeight: 40,
    maxHeight: 100,
    marginRight: 10,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    overflow: 'hidden',
  },
  sendButtonGradient: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
}); 