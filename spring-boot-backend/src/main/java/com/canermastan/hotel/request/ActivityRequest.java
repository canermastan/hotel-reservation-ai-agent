package com.canermastan.hotel.request;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class ActivityRequest {
    private String name;
    private String description;
    private Double price;
    private Integer capacity;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Long hotelId;
} 