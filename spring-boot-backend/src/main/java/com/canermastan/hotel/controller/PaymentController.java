package com.canermastan.hotel.controller;

import com.canermastan.hotel.mapper.DTOMapper;
import com.canermastan.hotel.service.PaymentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/payments")
@RequiredArgsConstructor
public class PaymentController {

    private final PaymentService paymentService;
    private final DTOMapper dtoMapper;

    /**
     * Process a payment for a reservation
     */
    @PostMapping("/process/{reservationId}")
    public ResponseEntity<Map<String, Object>> processPayment(
            @PathVariable Long reservationId,
            @RequestParam String paymentMethod,
            @RequestBody Map<String, String> paymentDetails) {
        
        Map<String, Object> result = paymentService.processPayment(
                reservationId, paymentMethod, paymentDetails);
        
        return ResponseEntity.ok(result);
    }
    
    /**
     * Refund a payment for a reservation
     */
    @PostMapping("/refund/{reservationId}")
    public ResponseEntity<Map<String, Object>> refundPayment(
            @PathVariable Long reservationId) {
        
        Map<String, Object> result = paymentService.refundPayment(reservationId);
        
        return ResponseEntity.ok(result);
    }
} 