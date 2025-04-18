import React, { useState } from 'react';
import axios from 'axios';
import { format } from 'date-fns';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Calendar } from '../components/ui/calendar';
import { Plane, Calendar as CalendarIcon, MapPin } from 'lucide-react';

interface Flight {
  flight_id: string;
  price_raw: number;
  price_formatted: string;
  origin_id: string;
  destination_id: string;
  departure_time: string;
  arrival_time: string;
  airline_name: string;
  flight_number: string;
  load_date: string;
  duration: string;
}

interface FlightAnalysis {
  cheapest_flight: Flight;
  average_price: number;
  fastest_flight: Flight;
  price_range: { min: number; max: number };
  airline_count: number;
}

const FlightSearchPage: React.FC = () => {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departureDate, setDepartureDate] = useState<Date | undefined>(undefined);
  const [flights, setFlights] = useState<Flight[]>([]);
  const [analysis, setAnalysis] = useState<FlightAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!origin || !destination || !departureDate) {
      setError('Please fill in all fields');
      return;
    }
    setLoading(true);
    setError('');
    const formattedDate = format(departureDate, 'yyyy-MM-dd');

    try {
      const flightResponse = await axios.get('http://localhost:8000/api/flights/search', {
        params: {
          origin_id: origin,
          destination_id: destination,
          departure_date: formattedDate,
        },
      });
      setFlights(flightResponse.data);

      const analysisResponse = await axios.get('http://localhost:8000/api/flights/analysis', {
        params: {
          origin_id: origin,
          destination_id: destination,
          departure_date: formattedDate,
        },
      });
      setAnalysis(analysisResponse.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch flights');
      setFlights([]);
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6 text-raspberry">Find Your Perfect Flight</h1>

      <div className="mb-8 p-6 bg-muted rounded-lg shadow-md">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Origin</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={origin}
                onChange={(e) => setOrigin(e.target.value.toUpperCase())}
                placeholder="e.g., HYD"
                className="pl-10"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Destination</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={destination}
                onChange={(e) => setDestination(e.target.value.toUpperCase())}
                placeholder="e.g., MIA"
                className="pl-10"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Departure Date</label>
            <Popover>
              <PopoverTrigger asChild>
                <div className="relative">
                  <CalendarIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={departureDate ? format(departureDate, 'yyyy-MM-dd') : ''}
                    readOnly
                    placeholder="Select date"
                    className="pl-10 cursor-pointer"
                  />
                </div>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar
                  mode="single"
                  selected={departureDate}
                  onSelect={setDepartureDate}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>
        </div>
        <Button
          onClick={handleSearch}
          disabled={loading}
          className="mt-4 bg-raspberry text-white hover:bg-raspberry/90"
        >
          {loading ? 'Searching...' : (
            <>
              <Plane className="mr-2 h-4 w-4" /> Search Flights
            </>
          )}
        </Button>
      </div>

      {error && <p className="text-destructive mb-4">{error}</p>}

      {analysis && (
        <div className="mb-8">
          <h2 className="text-2xl font-semibold mb-4 text-foreground">Flight Insights</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Best Deal</CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  Snag a deal with {analysis.cheapest_flight.airline_name} for{' '}
                  {analysis.cheapest_flight.price_formatted}! Wallet-friendly vibes. ✈️
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Quickest Trip</CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  Zoom to {destination} in {analysis.fastest_flight.duration} with{' '}
                  {analysis.fastest_flight.airline_name}. More time for fun! 🌴
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Price Scoop</CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  Prices range from ${analysis.price_range.min.toFixed(2)} to $
                  {analysis.price_range.max.toFixed(2)}. Average: $
                  {analysis.average_price.toFixed(2)}. Grab deals below average! 🕵️
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Airline Variety</CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  {analysis.airline_count} airline{analysis.airline_count > 1 ? 's' : ''} to choose
                  from. Pick your flavor! 🍗
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {flights.length > 0 && (
        <div>
          <h2 className="text-2xl font-semibold mb-4 text-foreground">
            Available Flights ({flights.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {flights.map((flight) => (
              <Card key={flight.flight_id}>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Plane className="mr-2 h-5 w-5 text-raspberry" /> {flight.airline_name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-bold text-amber">{flight.price_formatted}</p>
                  <p className="text-foreground">
                    {flight.origin_id} to {flight.destination_id}
                  </p>
                  <p className="text-muted-foreground">
                    Depart: {new Date(flight.departure_time).toLocaleString()}
                  </p>
                  <p className="text-muted-foreground">
                    Arrive: {new Date(flight.arrival_time).toLocaleString()}
                  </p>
                  <p className="text-foreground">Duration: {flight.duration}</p>
                  <p className="text-muted-foreground">Flight Number: {flight.flight_number}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FlightSearchPage;