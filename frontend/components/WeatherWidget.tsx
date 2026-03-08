"use client";

import React, { useState, useEffect } from "react";
import { Cloud, Sun, CloudRain, Snowflake, CloudLightning, Wind, Droplets, Eye, MapPin, RefreshCw } from "lucide-react";
import { cn } from "../lib/utils";

interface WeatherData {
  temperature: number;
  weatherCode: number;
  windSpeed: number;
  humidity: number;
  feelsLike: number;
  daily: {
    date: string;
    maxTemp: number;
    minTemp: number;
    weatherCode: number;
  }[];
  location: string;
}

const WMO_MAP: Record<number, { label: string; Icon: React.ElementType }> = {
  0: { label: "Clear sky", Icon: Sun },
  1: { label: "Mainly clear", Icon: Sun },
  2: { label: "Partly cloudy", Icon: Cloud },
  3: { label: "Overcast", Icon: Cloud },
  45: { label: "Fog", Icon: Eye },
  48: { label: "Depositing rime fog", Icon: Eye },
  51: { label: "Light drizzle", Icon: CloudRain },
  53: { label: "Moderate drizzle", Icon: CloudRain },
  55: { label: "Dense drizzle", Icon: CloudRain },
  61: { label: "Slight rain", Icon: CloudRain },
  63: { label: "Moderate rain", Icon: CloudRain },
  65: { label: "Heavy rain", Icon: CloudRain },
  71: { label: "Slight snow", Icon: Snowflake },
  73: { label: "Moderate snow", Icon: Snowflake },
  75: { label: "Heavy snow", Icon: Snowflake },
  80: { label: "Rain showers", Icon: CloudRain },
  81: { label: "Moderate showers", Icon: CloudRain },
  82: { label: "Violent showers", Icon: CloudRain },
  95: { label: "Thunderstorm", Icon: CloudLightning },
  96: { label: "Thunderstorm + hail", Icon: CloudLightning },
  99: { label: "Thunderstorm + heavy hail", Icon: CloudLightning },
};

function getWeatherInfo(code: number) {
  return WMO_MAP[code] ?? { label: "Unknown", Icon: Cloud };
}

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

interface WeatherWidgetProps {
  className?: string;
}

export default function WeatherWidget({ className }: WeatherWidgetProps) {
  const [data, setData] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWeather = async () => {
    setLoading(true);
    setError(null);

    try {
      // Get user's approximate location via browser geolocation or fallback to IP-based
      let lat: number | null = null;
      let lon: number | null = null;
      let locationName = "Your location";

      // Try browser geolocation first
      try {
        const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            timeout: 5000,
            enableHighAccuracy: false,
          })
        );
        lat = pos.coords.latitude;
        lon = pos.coords.longitude;
      } catch {
        // Geolocation denied or unavailable
      }

      // Fallback: IP-based geolocation
      if (lat === null || lon === null) {
        try {
          const ipResp = await fetch("https://ipapi.co/json/");
          if (ipResp.ok) {
            const ipData = await ipResp.json();
            lat = ipData.latitude;
            lon = ipData.longitude;
            locationName = ipData.city || ipData.region || "Your location";
          }
        } catch {
          // IP geolocation also failed
        }
      }

      // If all location methods failed, don't show weather
      if (lat === null || lon === null) {
        setError("Could not determine your location");
        setLoading(false);
        return;
      }

      // Reverse geocode if we got coords from browser (not IP which already gives city)
      if (locationName === "Your location") {
        try {
          const geoResp = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=10`,
            { headers: { "Accept-Language": "en" } }
          );
          if (geoResp.ok) {
            const geoData = await geoResp.json();
            locationName =
              geoData.address?.city ||
              geoData.address?.town ||
              geoData.address?.village ||
              geoData.address?.county ||
              "Your location";
          }
        } catch {
          // Reverse geocode failed
        }
      }

      const weatherResp = await fetch(
        `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto&forecast_days=7`
      );
      if (!weatherResp.ok) throw new Error("Weather API failed");

      const weather = await weatherResp.json();

      setData({
        temperature: Math.round(weather.current.temperature_2m),
        weatherCode: weather.current.weather_code,
        windSpeed: Math.round(weather.current.wind_speed_10m),
        humidity: weather.current.relative_humidity_2m,
        feelsLike: Math.round(weather.current.apparent_temperature),
        location: locationName,
        daily: weather.daily.time.slice(1, 6).map((date: string, i: number) => ({
          date,
          maxTemp: Math.round(weather.daily.temperature_2m_max[i + 1]),
          minTemp: Math.round(weather.daily.temperature_2m_min[i + 1]),
          weatherCode: weather.daily.weather_code[i + 1],
        })),
      });
    } catch (e) {
      setError("Could not load weather data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeather();
  }, []);

  if (loading) {
    return (
      <div className={cn("bg-glass/30 backdrop-blur-xl border border-foreground/10 rounded-2xl p-6 animate-pulse", className)}>
        <div className="h-4 w-24 bg-foreground/10 rounded mb-4" />
        <div className="h-12 w-20 bg-foreground/10 rounded mb-4" />
        <div className="flex gap-2">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="h-16 flex-1 bg-foreground/5 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return null; // Silently fail — don't break the landing page
  }

  const current = getWeatherInfo(data.weatherCode);
  const CurrentIcon = current.Icon;

  return (
    <div className={cn("bg-glass/30 backdrop-blur-xl border border-foreground/10 rounded-2xl p-5 md:p-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-foreground/60">
          <MapPin className="w-3.5 h-3.5" />
          <span className="text-xs font-medium">{data.location}</span>
        </div>
        <button
          onClick={fetchWeather}
          className="p-1.5 rounded-full hover:bg-foreground/10 text-foreground/40 hover:text-foreground transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Current */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-4xl font-light text-foreground tracking-tight">{data.temperature}°</div>
          <div className="text-sm text-foreground/60 mt-1">{current.label}</div>
        </div>
        <CurrentIcon className="w-12 h-12 text-accent/80" />
      </div>

      {/* Stats */}
      <div className="flex gap-4 mb-5 text-xs text-foreground/50">
        <div className="flex items-center gap-1">
          <Droplets className="w-3 h-3" />
          {data.humidity}%
        </div>
        <div className="flex items-center gap-1">
          <Wind className="w-3 h-3" />
          {data.windSpeed} km/h
        </div>
        <div>Feels {data.feelsLike}°</div>
      </div>

      {/* 5-Day Forecast */}
      <div className="flex gap-1.5">
        {data.daily.map((day) => {
          const info = getWeatherInfo(day.weatherCode);
          const DayIcon = info.Icon;
          const d = new Date(day.date);
          return (
            <div
              key={day.date}
              className="flex-1 flex flex-col items-center gap-1 py-2 px-1 rounded-lg bg-foreground/5 border border-foreground/5"
            >
              <span className="text-[10px] font-medium text-foreground/50">
                {DAY_NAMES[d.getDay()]}
              </span>
              <DayIcon className="w-4 h-4 text-foreground/60" />
              <div className="flex gap-1 text-[10px]">
                <span className="text-foreground">{day.maxTemp}°</span>
                <span className="text-foreground/40">{day.minTemp}°</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
