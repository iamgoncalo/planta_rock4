FROM eclipse-mosquitto:2.0
COPY mosquitto.conf /mosquitto/config/mosquitto.conf
RUN mosquitto_passwd -c -b /mosquitto/config/passwd plantaos planta2026mqtt
RUN mosquitto_passwd -b /mosquitto/config/passwd WC-01 planta2026mqtt
RUN mosquitto_passwd -b /mosquitto/config/passwd WC-02 planta2026mqtt
RUN mosquitto_passwd -b /mosquitto/config/passwd WC-03 planta2026mqtt
RUN mosquitto_passwd -b /mosquitto/config/passwd WC-04 planta2026mqtt
RUN mosquitto_passwd -b /mosquitto/config/passwd WC-05 planta2026mqtt
RUN mosquitto_passwd -b /mosquitto/config/passwd WC-06 planta2026mqtt
RUN mosquitto_passwd -b /mosquitto/config/passwd WC-07 planta2026mqtt
RUN mosquitto_passwd -b /mosquitto/config/passwd WC-08 planta2026mqtt
EXPOSE 1883 9001
