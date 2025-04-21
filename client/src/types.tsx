export type User = {
    _id: string;
    email: string;
    name: string;
    addressLine1: string;
    city: string;
    country: string;
  };

  export type TravelResponse = {
    status: string;   
    answer: string;   
    model: string;
    chat_id?: string;
    location?: string;
    hotels?: {
      data: Array<{
        chainCode: string;
        name: string;
        hotelId: string;
        geoCode: {
          latitude: number;
          longitude: number;
        };
        address: {
          countryCode: string;
        };
        rating: number;
      }>;
      offers: Array<any>; // This is empty in the example but included in the type
      meta: {
        count: number;
        offersCount: number;
      };
      request: {
        checkInDate: string;
        checkOutDate: string;
        adults: number;
        ratings: string;
      };
    };
    attractions?: {
      attractions_list: {
        location: string;
        attractions: Array<{
          name: string;
          address: string;
          rating: number;
          total_ratings: number;
          photo_url: string;
          location: {
            lat: number;
            lng: number;
          };
          types: string[];
        }>;
      };
    };
    // attractions?: Array<{
    //   name: string;
    //   address: string;
    //   rating: number;
    //   total_ratings: number;
    //   photo_url: string;
    //   location: {
    //     lat: number;
    //     lng: number;
    //   };
    //   types: string[];
    // }>;
    attractions_list?: {
      attractions: Array<{
        name: string;
        address: string;
        location: {
          lat: number;
          lng: number;
        };
        rating: number;
        photo_url: string;
        total_ratings: number;
        types: string[];
      }>;
      length: number;
    };
    restaurants?: Array<{
      name: string;
      address: string;
      rating: number;
      total_ratings: number;
      photo_url: string;
      location: {
        lat: number;
        lng: number;
      };
      types: string[];
    }>;
    flights?: {
      meta: {
        count: number;
        origin: string;
        destination: string;
        departureDate: string;
        passengers: number;
        passengerType: string;
      };
      data: Array<{
        id: string;
        carrier: string;
        carrierName: string;
        departure: {
          iataCode: string;
          terminal: string;
          at: string;
        };
        arrival: {
          iataCode: string;
          terminal: string;
          at: string;
        };
        duration: string;
        price: {
          currency: string;
          total: string;
          perAdult: string;
        };
        cabinClass: string;
        baggage: {
          checkedBags: number;
          cabinBags: number;
        }
      }>;
    };
    query?: {
      location: string;
    };
  };