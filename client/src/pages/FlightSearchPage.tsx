import React, { useState } from 'react';
import axios from 'axios';
import { format } from 'date-fns';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plane, Calendar as CalendarIcon } from 'lucide-react';
import Layout from '@/layouts/layout';
import { cn } from '@/lib/utils';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';

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

// Create a simple date picker component using shadcn components
const DatePickerInput = ({ value, onChange, placeholder }: {
  value?: Date;
  onChange: (date?: Date) => void;
  placeholder: string;
}) => {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant={"outline"}
          className={cn(
            "w-full justify-start text-left font-normal",
            !value && "text-muted-foreground"
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {value ? format(value, 'PPP') : <span>{placeholder}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={value}
          onSelect={onChange}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  );
};

const FlightSearchPage: React.FC = () => {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departureDate, setDepartureDate] = useState<Date | undefined>(undefined);
  const [returnDate, setReturnDate] = useState<Date | undefined>(undefined);
  const [flights, setFlights] = useState<Flight[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!origin || !destination || !departureDate) {
      setError('Please fill in all required fields');
      return;
    }
    
    setLoading(true);
    setError('');

    try {
      const formattedDepartureDate = format(departureDate, 'yyyy-MM-dd');
      
      const flightResponse = await axios.get('http://localhost:8000/api/flights/search', {
        params: {
          origin_id: origin.toUpperCase(),
          destination_id: destination.toUpperCase(),
          departure_date: formattedDepartureDate,
        },
      });
      
      setFlights(flightResponse.data);
      
      if (flightResponse.data.length === 0) {
        setError('No flights found for the selected criteria. Try different dates or destinations.');
      }
    } catch (err: any) {
      console.error('Error fetching flights:', err);
      setError(err.response?.data?.detail || 'Failed to fetch flights');
      setFlights([]);
    } finally {
      setLoading(false);
    }
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    } catch (error) {
      return dateString;
    }
  };

  return (
    <Layout showSidebar={true} showHero={false} showFooter={false}>
      <div className="container mx-auto p-4">
        <h1 className="text-3xl font-bold mb-6 text-foreground">Find Your Perfect Flight</h1>

        <div className="mb-8 p-6 bg-muted rounded-lg shadow-md">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Origin</label>
              <Input
                value={origin}
                onChange={(e) => setOrigin(e.target.value.toUpperCase())}
                placeholder="e.g., BOS"
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Destination</label>
              <Input
                value={destination}
                onChange={(e) => setDestination(e.target.value.toUpperCase())}
                placeholder="e.g., HYD"
                className="w-full"
              />
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Departure Date</label>
              <DatePickerInput 
                value={departureDate} 
                onChange={setDepartureDate} 
                placeholder="Select departure date"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Return Date (Optional)</label>
              <DatePickerInput 
                value={returnDate} 
                onChange={setReturnDate} 
                placeholder="Select return date"
              />
            </div>
          </div>
          
          <Button
            onClick={handleSearch}
            disabled={loading}
            className="mt-4 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {loading ? 'Searching...' : (
              <>
                <Plane className="mr-2 h-4 w-4" /> Search Flights
              </>
            )}
          </Button>
        </div>

        {error && <p className="text-destructive mb-4">{error}</p>}

        {loading ? (
          <div className="flex justify-center items-center p-8">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : flights.length > 0 ? (
          <div>
            <h2 className="text-2xl font-semibold mb-4 text-foreground">
              Available Flights ({flights.length})
            </h2>
            <div className="grid grid-cols-1 gap-6">
              {flights.map((flight) => (
                <Card key={flight.flight_id} className="overflow-hidden">
                  <CardHeader className="bg-primary/5 pb-2">
                    <CardTitle className="flex justify-between items-center">
                      <div className="flex items-center">
                        <Plane className="mr-2 h-5 w-5 text-primary" /> 
                        {flight.airline_name} - {flight.flight_number}
                      </div>
                      <div className="text-lg font-bold text-primary">{flight.price_formatted}</div>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <p className="font-semibold mb-1">Departure</p>
                        <p className="text-muted-foreground">
                          {formatDate(flight.departure_time)}
                        </p>
                        <p className="text-muted-foreground">{flight.origin_id}</p>
                      </div>
                      <div>
                        <p className="font-semibold mb-1">Arrival</p>
                        <p className="text-muted-foreground">
                          {formatDate(flight.arrival_time)}
                        </p>
                        <p className="text-muted-foreground">{flight.destination_id}</p>
                      </div>
                    </div>
                    <div className="mt-4 flex justify-between items-center">
                      <div>
                        <p className="font-semibold">Duration: {flight.duration}</p>
                      </div>
                      <Button 
                        className="bg-primary text-primary-foreground hover:bg-primary/90"
                        onClick={() => window.open(`https://www.${flight.airline_name.toLowerCase().replace(/\s+/g, '')}.com`, '_blank')}
                      >
                        Select
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </Layout>
  );
};

export default FlightSearchPage;