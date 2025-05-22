package com.canermastan.hotel.service;

import com.canermastan.hotel.entity.Hotel;
import com.canermastan.hotel.entity.Room;
import com.canermastan.hotel.repository.HotelRepository;
import com.canermastan.hotel.repository.RoomRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class HotelService {

    private final HotelRepository hotelRepository;
    private final RoomRepository roomRepository;
    private final RoomService roomService;

    public List<Hotel> getAllHotels() {
        return hotelRepository.findAll();
    }

    public List<Hotel> searchHotels(String city, Double minPrice, Double maxPrice) {
        return hotelRepository.search(city, minPrice, maxPrice);
    }

    public Optional<Hotel> getHotelById(Long id) {
        return hotelRepository.findById(id);
    }

    public Hotel createHotel(Hotel hotel) {
        // Set available rooms equal to total rooms when creating a new hotel
        if (hotel.getTotalRooms() != null && hotel.getAvailableRooms() == null) {
            hotel.setAvailableRooms(hotel.getTotalRooms());
        }
        return hotelRepository.save(hotel);
    }

    public Hotel updateHotel(Long id, Hotel hotelDetails) {
        Hotel hotel = hotelRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Hotel not found"));
        
        hotel.setName(hotelDetails.getName());
        hotel.setCity(hotelDetails.getCity());
        hotel.setAddress(hotelDetails.getAddress());
        hotel.setDescription(hotelDetails.getDescription());
        hotel.setPricePerNight(hotelDetails.getPricePerNight());
        
        // Don't update totalRooms and availableRooms directly from request
        // as this could create inconsistencies
        
        return hotelRepository.save(hotel);
    }

    public void deleteHotel(Long id) {
        Hotel hotel = hotelRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Hotel not found"));
        
        // Check if there are any rooms
        List<Room> rooms = roomRepository.findByHotelId(id);
        if (!rooms.isEmpty()) {
            throw new IllegalStateException("Cannot delete hotel with existing rooms");
        }
        
        hotelRepository.delete(hotel);
    }

    public Map<String, Object> checkAvailability(Long hotelId, LocalDate checkIn, LocalDate checkOut) {
        Hotel hotel = hotelRepository.findById(hotelId)
                .orElseThrow(() -> new IllegalArgumentException("Hotel not found"));
        
        // Get available rooms for this date range
        List<Room> availableRooms = roomService.getAvailableRooms(hotelId, checkIn, checkOut);
        
        Map<String, Object> result = new HashMap<>();
        result.put("hotelId", hotelId);
        result.put("hotelName", hotel.getName());
        result.put("checkInDate", checkIn);
        result.put("checkOutDate", checkOut);
        result.put("availableRoomsCount", availableRooms.size());
        result.put("availableRooms", availableRooms);
        result.put("isAvailable", !availableRooms.isEmpty());
        
        return result;
    }
    
    public long countHotelsByCity(String city) {
        return hotelRepository.countByCity(city);
    }
} 