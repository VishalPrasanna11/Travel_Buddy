import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { format, addDays, isAfter, isBefore, isEqual } from 'date-fns';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plane, Calendar as CalendarIcon, ArrowRightLeft, Loader2 } from 'lucide-react';
import Layout from '@/layouts/layout';
import { cn } from '@/lib/utils';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { toast } from "sonner";
import { DatePicker } from "@/components/ui/date-picker";
import { InlineDatePicker } from "@/components/ui/inline-date-picker";

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

const FlightSearchPage: React.FC = () => {
  const [tripType, setTripType] = useState<'one-way' | 'round-trip'>('one-way');
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departureDate, setDepartureDate] = useState<Date | undefined>(addDays(new Date(), 7));
  const [returnDate, setReturnDate] = useState<Date | undefined>(addDays(new Date(), 14));
  const [flights, setFlights] = useState<Flight[]>([]);
  const [returnFlights, setReturnFlights] = useState<Flight[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<{
    origin?: string;
    destination?: string;
    departureDate?: string;
    returnDate?: string;
  }>({});
  
  // Swap origin and destination
  const handleSwapLocations = () => {
    setOrigin(destination);
    setDestination(origin);
  };
  
  // Update return date if departure date changes and return date is before it
  useEffect(() => {
    if (departureDate && returnDate) {
      if (isBefore(returnDate, departureDate) || isEqual(returnDate, departureDate)) {
        setReturnDate(addDays(departureDate, 7));
      }
    }
  }, [departureDate]);
  
  // Handle trip type change
  const handleTripTypeChange = (value: string) => {
    setTripType(value as 'one-way' | 'round-trip');
    if (value === 'one-way') {
      setReturnDate(undefined);
    } else if (!returnDate) {
      setReturnDate(departureDate ? addDays(departureDate, 7) : addDays(new Date(), 14));
    }
  };

  const validateForm = () => {
    const errors: {
      origin?: string;
      destination?: string;
      departureDate?: string;
      returnDate?: string;
    } = {};
    
    if (!origin.trim()) {
      errors.origin = 'Origin is required';
    }
    
    if (!destination.trim()) {
      errors.destination = 'Destination is required';
    } else if (destination.trim().toUpperCase() === origin.trim().toUpperCase()) {
      errors.destination = 'Destination must be different from origin';
    }
    
    if (!departureDate) {
      errors.departureDate = 'Departure date is required';
    }
    
    if (tripType === 'round-trip' && !returnDate) {
      errors.returnDate = 'Return date is required for round-trip';
    }
    
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSearch = async () => {
    if (!validateForm()) {
      return;
    }
    
    setLoading(true);
    setError('');
    setFlights([]);
    setReturnFlights([]);

    try {
      // Mock flight data for testing since the backend is returning 500 errors
      setTimeout(() => {
        const mockFlights = [
          {
            flight_id: "FL123",
            price_raw: 450,
            price_formatted: "$450",
            origin_id: origin,
            destination_id: destination,
            departure_time: departureDate ? departureDate.toISOString() : new Date().toISOString(),
            arrival_time: departureDate ? new Date(departureDate.getTime() + 5 * 60 * 60 * 1000).toISOString() : new Date().toISOString(),
            airline_name: "Sky Airways",
            flight_number: "SA-1234",
            load_date: new Date().toISOString(),
            duration: "5h 10m"
          },
          {
            flight_id: "FL456",
            price_raw: 550,
            price_formatted: "$550",
            origin_id: origin,
            destination_id: destination,
            departure_time: departureDate ? new Date(departureDate.getTime() + 2 * 60 * 60 * 1000).toISOString() : new Date().toISOString(),
            arrival_time: departureDate ? new Date(departureDate.getTime() + 7 * 60 * 60 * 1000).toISOString() : new Date().toISOString(),
            airline_name: "Global Airlines",
            flight_number: "GA-5678",
            load_date: new Date().toISOString(),
            duration: "4h 45m"
          }
        ];
        
        setFlights(mockFlights);
        
        // If round-trip, set mock return flights
        if (tripType === 'round-trip' && returnDate) {
          const mockReturnFlights = [
            {
              flight_id: "FL789",
              price_raw: 480,
              price_formatted: "$480",
              origin_id: destination,
              destination_id: origin,
              departure_time: returnDate ? returnDate.toISOString() : new Date().toISOString(),
              arrival_time: returnDate ? new Date(returnDate.getTime() + 5 * 60 * 60 * 1000).toISOString() : new Date().toISOString(),
              airline_name: "Sky Airways",
              flight_number: "SA-9876",
              load_date: new Date().toISOString(),
              duration: "5h 30m"
            },
            {
              flight_id: "FL012",
              price_raw: 520,
              price_formatted: "$520",
              origin_id: destination,
              destination_id: origin,
              departure_time: returnDate ? new Date(returnDate.getTime() + 3 * 60 * 60 * 1000).toISOString() : new Date().toISOString(),
              arrival_time: returnDate ? new Date(returnDate.getTime() + 8 * 60 * 60 * 1000).toISOString() : new Date().toISOString(),
              airline_name: "Global Airlines",
              flight_number: "GA-5432",
              load_date: new Date().toISOString(),
              duration: "5h 15m"
            }
          ];
          
          setReturnFlights(mockReturnFlights);
        }
        
        setLoading(false);
      }, 1500); // Simulate loading time

      /* Commented out the actual API calls until backend is fixed
      const formattedDepartureDate = departureDate ? format(departureDate, 'yyyy-MM-dd') : '';
      
      // Fetch outbound flights
      const flightResponse = await axios.get('http://localhost:8000/api/flights/search', {
        params: {
          origin_id: origin.toUpperCase(),
          destination_id: destination.toUpperCase(),
          departure_date: formattedDepartureDate,
        },
      });
      
      setFlights(flightResponse.data);
      
      // If round-trip, fetch return flights
      if (tripType === 'round-trip' && returnDate) {
        const formattedReturnDate = format(returnDate, 'yyyy-MM-dd');
        
        const returnFlightResponse = await axios.get('http://localhost:8000/api/flights/search', {
          params: {
            origin_id: destination.toUpperCase(),
            destination_id: origin.toUpperCase(),
            departure_date: formattedReturnDate,
          },
        });
        
        setReturnFlights(returnFlightResponse.data);
      }
      
      if (flightResponse.data.length === 0) {
        setError('No outbound flights found for the selected criteria. Try different dates or destinations.');
      } else if (tripType === 'round-trip' && returnFlights.length === 0) {
        setError('No return flights found for the selected criteria. Try different dates.');
      }
      */
    } catch (err: any) {
      console.error('Error fetching flights:', err);
      setError(err.response?.data?.detail || 'Failed to fetch flights');
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
          {/* Trip Type Selector */}
          <div className="mb-4">
            <Tabs defaultValue="one-way" onValueChange={handleTripTypeChange} value={tripType}>
              <TabsList className="grid w-full max-w-xs grid-cols-2">
                <TabsTrigger value="one-way">One Way</TabsTrigger>
                <TabsTrigger value="round-trip">Round Trip</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
          
          {/* Origin and Destination */}
          <div className="relative grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Origin</label>
              <Input
                value={origin}
                onChange={(e) => setOrigin(e.target.value.toUpperCase())}
                placeholder="e.g., BOS"
                className={cn("w-full", fieldErrors.origin && "border-destructive focus:ring-destructive")}
                disabled={loading}
              />
              {fieldErrors.origin && <p className="text-xs text-destructive mt-1">{fieldErrors.origin}</p>}
            </div>
            
            {/* Swap Button (for desktop) */}
            <div className="hidden md:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button 
                      variant="outline" 
                      size="icon" 
                      className="rounded-full bg-background shadow-md" 
                      onClick={handleSwapLocations}
                      disabled={loading}
                    >
                      <ArrowRightLeft className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Swap origin and destination</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Destination</label>
              <Input
                value={destination}
                onChange={(e) => setDestination(e.target.value.toUpperCase())}
                placeholder="e.g., HYD"
                className={cn("w-full", fieldErrors.destination && "border-destructive focus:ring-destructive")}
                disabled={loading}
              />
              {fieldErrors.destination && <p className="text-xs text-destructive mt-1">{fieldErrors.destination}</p>}
            </div>
            
            {/* Swap Button (for mobile) */}
            <div className="md:hidden flex justify-center my-2">
              <Button 
                variant="outline" 
                size="sm" 
                className="flex items-center gap-2" 
                onClick={handleSwapLocations}
                disabled={loading}
              >
                <ArrowRightLeft className="h-4 w-4" /> Swap
              </Button>
            </div>
          </div>
          
          {/* Date Selection */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Departure Date
                <Badge variant="outline" className="ml-2 font-normal">Required</Badge>
              </label>
              <InlineDatePicker
                date={departureDate}
                setDate={(date) => {
                  if (date) {
                    setDepartureDate(date);
                    toast.success("Departure date updated to " + format(date, 'MMM d, yyyy'));
                  }
                }}
                placeholder="Select departure date"
                minDate={new Date()}
                disabled={loading}
                className={fieldErrors.departureDate ? "border-destructive focus:ring-destructive" : ""}
              />
              {fieldErrors.departureDate && <p className="text-xs text-destructive mt-1">{fieldErrors.departureDate}</p>}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Return Date
                {tripType === "round-trip" ? (
                  <Badge variant="outline" className="ml-2 font-normal">Required</Badge>
                ) : (
                  <Badge variant="outline" className="ml-2 font-normal">Optional</Badge>
                )}
              </label>
              <InlineDatePicker
                date={returnDate}
                setDate={(date) => {
                  if (date) {
                    setReturnDate(date);
                    toast.success("Return date updated to " + format(date, 'MMM d, yyyy'));
                  }
                }}
                placeholder="Select return date"
                minDate={departureDate ? addDays(departureDate, 0) : new Date()}
                disabled={loading || tripType === "one-way"}
                className={fieldErrors.returnDate ? "border-destructive focus:ring-destructive" : ""}
              />
              {fieldErrors.returnDate && <p className="text-xs text-destructive mt-1">{fieldErrors.returnDate}</p>}
            </div>
          </div>
          
          <Button
            onClick={handleSearch}
            disabled={loading}
            className="mt-6 bg-primary text-primary-foreground hover:bg-primary/90 w-full md:w-auto"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Searching Flights...
              </>
            ) : (
              <>
                <Plane className="mr-2 h-4 w-4" /> Search Flights
              </>
            )}
          </Button>
        </div>

        {error && <div className="rounded-md bg-destructive/10 p-3 text-destructive mb-6">{error}</div>}

        {loading ? (
          <div className="flex flex-col justify-center items-center p-12">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="text-muted-foreground">Searching for the best flight deals...</p>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Outbound Flights */}
            {flights.length > 0 && (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <Badge variant="outline" className="bg-primary/10 text-primary">
                    Outbound
                  </Badge>
                  <h2 className="text-2xl font-semibold text-foreground">
                    {origin} to {destination} · {flights.length} {flights.length === 1 ? 'flight' : 'flights'}
                  </h2>
                </div>
                <div className="grid grid-cols-1 gap-6">
                  {flights.map((flight) => (
                    <Card key={flight.flight_id} className="overflow-hidden hover:shadow-md transition-all">
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
            )}
            
            {/* Return Flights */}
            {tripType === 'round-trip' && returnFlights.length > 0 && (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <Badge variant="outline" className="bg-amber-500/10 text-amber-600">
                    Return
                  </Badge>
                  <h2 className="text-2xl font-semibold text-foreground">
                    {destination} to {origin} · {returnFlights.length} {returnFlights.length === 1 ? 'flight' : 'flights'}
                  </h2>
                </div>
                <div className="grid grid-cols-1 gap-6">
                  {returnFlights.map((flight) => (
                    <Card key={flight.flight_id} className="overflow-hidden hover:shadow-md transition-all">
                      <CardHeader className="bg-amber-500/5 pb-2">
                        <CardTitle className="flex justify-between items-center">
                          <div className="flex items-center">
                            <Plane className="mr-2 h-5 w-5 text-amber-600" /> 
                            {flight.airline_name} - {flight.flight_number}
                          </div>
                          <div className="text-lg font-bold text-amber-600">{flight.price_formatted}</div>
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
                            variant="outline"
                            className="border-amber-500 text-amber-600 hover:bg-amber-500/10"
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
            )}
            
            {/* No flights found message */}
            {!loading && flights.length === 0 && !error && (
              <div className="text-center py-12">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
                  <Plane className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-xl font-medium mb-2">Ready to search for flights</h3>
                <p className="text-muted-foreground">
                  Enter your travel details above and click 'Search Flights' to find the best flight deals.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default FlightSearchPage;