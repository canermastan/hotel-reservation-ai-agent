package com.canermastan.hotel.repository;

import com.canermastan.hotel.entity.Reservation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ReservationRepository extends JpaRepository<Reservation, Long> {
    List<Reservation> findByHotelId(Long hotelId);
    List<Reservation> findByRoomId(Long roomId);
}
