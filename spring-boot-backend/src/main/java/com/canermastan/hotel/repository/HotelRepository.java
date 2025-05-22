package com.canermastan.hotel.repository;

import com.canermastan.hotel.entity.Hotel;
import feign.Param;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface HotelRepository extends JpaRepository<Hotel, Long> {
    List<Hotel> findByCityIgnoreCase(String city);

    @Query("SELECT COUNT(h) FROM Hotel h WHERE LOWER(h.city) = LOWER(:city)")
    long countByCity(@Param("city") String city);

    @Query("SELECT h FROM Hotel h WHERE "
            + "(:city IS NULL OR LOWER(h.city) = LOWER(:city)) AND "
            + "(:minPrice IS NULL OR h.pricePerNight >= :minPrice) AND "
            + "(:maxPrice IS NULL OR h.pricePerNight <= :maxPrice)")
    List<Hotel> search(
            @Param("city") String city,
            @Param("minPrice") Double minPrice,
            @Param("maxPrice") Double maxPrice
    );
}
